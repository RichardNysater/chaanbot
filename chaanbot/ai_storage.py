"""SQLite history and usage accounting for the optional AI module."""

from contextlib import closing
from datetime import datetime, timezone
import math
import time
from typing import List, Optional, Tuple

from chaanbot.database import Database


class AiStorage:
    """Keep room/user history and reserve user-wide and global daily budgets."""

    def __init__(self, database: Database, cooldown: int, daily_requests: int,
                 daily_tokens: int, global_daily_requests: int, global_daily_tokens: int,
                 history_bytes: int, history_turns: int, history_ttl: int):
        self.database = database
        self.cooldown = cooldown
        self.daily_requests = daily_requests
        self.daily_tokens = daily_tokens
        self.global_daily_requests = global_daily_requests
        self.global_daily_tokens = global_daily_tokens
        self.history_bytes = history_bytes
        self.history_turns = history_turns
        self.history_ttl = history_ttl
        if database:
            self._initialize_database()

    def _initialize_database(self) -> None:
        """Create tables and retain compatibility with existing request records."""
        with closing(self.database.connect()) as conn, conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS ai_history (
                    id INTEGER PRIMARY KEY, room_id TEXT NOT NULL,
                    user_id TEXT NOT NULL, query TEXT NOT NULL,
                    answer TEXT NOT NULL, created REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS ai_history_owner
                    ON ai_history(room_id, user_id, id);
                CREATE TABLE IF NOT EXISTS ai_requests (
                    event_id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                    day TEXT NOT NULL, started REAL NOT NULL,
                    tokens INTEGER NOT NULL, pending INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS ai_requests_day
                    ON ai_requests(day, user_id);
            """)
            columns = {row[1] for row in conn.execute("PRAGMA table_info(ai_requests)")}
            added_columns = {
                "chargeable": "INTEGER NOT NULL DEFAULT 1",
                "delivery": "TEXT NOT NULL DEFAULT 'none'",
            }
            for name, definition in added_columns.items():
                if name not in columns:
                    conn.execute("ALTER TABLE ai_requests ADD COLUMN " + name + " " + definition)

    @staticmethod
    def _day() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def reserve(self, event_id: str, user_id: str, tokens: int) -> Optional[str]:
        """Reserve usage atomically, returning a rejection message when a limit applies."""
        now = time.time()
        day = self._day()
        with closing(self.database.connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM ai_requests WHERE event_id=?", (event_id,)).fetchone():
                return "This AI request has already been handled."
            recent = conn.execute("SELECT MAX(started) FROM ai_requests WHERE user_id=? AND chargeable=1",
                                  (user_id,)).fetchone()[0]
            if recent is not None and now - recent < self.cooldown:
                return "AI cooldown: wait {} seconds.".format(math.ceil(self.cooldown - (now - recent)))
            if conn.execute("SELECT 1 FROM ai_requests WHERE user_id=? AND pending=1 AND started>?",
                            (user_id, now - 180)).fetchone():
                return "You already have an AI request in progress."
            count, used = conn.execute("SELECT COUNT(*), COALESCE(SUM(tokens),0) FROM ai_requests "
                                      "WHERE day=? AND user_id=? AND chargeable=1", (day, user_id)).fetchone()
            if count >= self.daily_requests or used + tokens > self.daily_tokens:
                return "Your daily AI budget is exhausted or too low for another request. Resets at 00:00 UTC."
            count, used = conn.execute("SELECT COUNT(*), COALESCE(SUM(tokens),0) FROM ai_requests "
                                      "WHERE day=? AND chargeable=1", (day,)).fetchone()
            if count >= self.global_daily_requests or used + tokens > self.global_daily_tokens:
                return "The bot's daily AI budget is exhausted. Resets at 00:00 UTC."
            conn.execute("INSERT INTO ai_requests(event_id,user_id,day,started,tokens,pending) VALUES (?,?,?,?,?,1)",
                         (event_id, user_id, day, now, tokens))
            conn.execute("DELETE FROM ai_requests WHERE started<?", (now - 7 * 86400,))
        return None

    def usage(self, user_id: str) -> Tuple[int, int]:
        """Return today's charged request and token totals across all rooms."""
        with closing(self.database.connect()) as conn:
            count, tokens = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(tokens),0) FROM ai_requests "
                "WHERE day=? AND user_id=? AND chargeable=1",
                (self._day(), user_id)).fetchone()
        return count, tokens

    def history(self, room_id: str, user_id: str) -> List[dict]:
        """Return the bounded, unexpired conversation in chronological order."""
        with closing(self.database.connect()) as conn, conn:
            conn.execute("DELETE FROM ai_history WHERE created<?", (time.time() - self.history_ttl,))
            rows = conn.execute("SELECT query,answer FROM ai_history WHERE room_id=? AND user_id=? "
                                "ORDER BY id DESC LIMIT ?",
                                (room_id, user_id, self.history_turns)).fetchall()
        result = []
        size = 0
        for query, answer in rows:
            size += len(query.encode("utf-8")) + len(answer.encode("utf-8"))
            if size > self.history_bytes:
                break
            result[0:0] = [
                {"role": "user", "content": query},
                {"role": "assistant", "content": answer},
            ]
        return result

    def save_history(self, room_id: str, user_id: str, query: str, answer: str) -> None:
        """Record a delivered answer and retain only the configured number of turns."""
        with closing(self.database.connect()) as conn, conn:
            conn.execute("INSERT INTO ai_history(room_id,user_id,query,answer,created) VALUES(?,?,?,?,?)",
                         (room_id, user_id, query, answer, time.time()))
            conn.execute("DELETE FROM ai_history WHERE room_id=? AND user_id=? AND id NOT IN "
                         "(SELECT id FROM ai_history WHERE room_id=? AND user_id=? ORDER BY id DESC LIMIT ?)",
                         (room_id, user_id, room_id, user_id, self.history_turns))

    def reset_history(self, room_id: str, user_id: str, request_in_progress: bool = False) -> bool:
        """Clear one conversation only when the user has no active request."""
        with closing(self.database.connect()) as conn, conn:
            if request_in_progress or conn.execute(
                    "SELECT 1 FROM ai_requests WHERE user_id=? AND pending=1 AND started>?",
                    (user_id, time.time() - 180)).fetchone():
                return False
            conn.execute("DELETE FROM ai_history WHERE room_id=? AND user_id=?", (room_id, user_id))
        return True

    def finish(self, event_id: str, tokens: int, chargeable: bool, delivery: str) -> None:
        """Finalize a pending reservation without changing an already completed request."""
        with closing(self.database.connect()) as conn, conn:
            conn.execute(
                "UPDATE ai_requests SET tokens=?,pending=0,chargeable=?,delivery=? "
                "WHERE event_id=? AND pending=1",
                (tokens, int(chargeable), delivery, event_id))
