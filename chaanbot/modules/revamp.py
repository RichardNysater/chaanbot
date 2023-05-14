""" The revamp module turns AMP urls into normal URLS
Available commands:
None, will trigger on any AMP link.
Usage example:
[Xhark]: https://news.com/amp/russia-loses-ukraine-war
Would results in:
"Bot: https://news.com/russia-loses-ukraine-war"
"""

import os
import re

from nio import RoomMessage, MatrixRoom

from chaanbot.database import Database
from chaanbot.matrix import Matrix


class Revamp:
    always_run = True  # Run on all messages, even if other modules has activated
    output_message_prefix = ""

    def __init__(self, config, matrix: Matrix, database: Database, requests):
        self.matrix = matrix
        self.requests = requests
        self.output_message_prefix = config.get("revamp", "prefix_message",
                                                fallback="Fixed your link(s): ")

    async def run(self, room: MatrixRoom, event: RoomMessage, message) -> bool:
        links = re.findall(r"http[s]*://[^\s]+/amp/[^\s]+", message, re.IGNORECASE)
        hits = [link.replace("/amp/", "/") for link in links]
        if hits:
            msg = self.output_message_prefix + os.linesep.join(hits)
            await self.matrix.send_text_to_room(msg, room.room_id)

        return False  # The module does not use commands and should not return that it has handled one
