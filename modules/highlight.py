import logging

import command_utility

logger = logging.getLogger("highlight")


class Highlight:
    config = {
        "always_run": False,
        "commands": {"highlight_all": ["!hlall", "!highlightall"],
                     "highlight_group": ["!hlg", "!highlightgroup", "!hlgroup"],
                     "add_to_group": ["!hla", "!hladd", "!highlightadd"],
                     "delete_from_group": ["!hld", "!hldelete", "!highlightdelete"],
                     "highlight": ["!hl", "!highlight"]},
    }

    def __init__(self, matrix, database):
        self.database = database
        self.matrix = matrix
        logger.debug("Initializing highlight database if needed")
        conn = database.connect()
        conn.execute('''CREATE TABLE IF NOT EXISTS highlight_groups
        (ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        ROOM_ID TEXT NOT NULL,
        "GROUP_NAME" TEXT NOT NULL,
        MEMBER TEXT NOT NULL,
        UNIQUE(ROOM_ID,GROUP_NAME,MEMBER));    
        ''')
        conn.commit()

    def run(self, room, event, message) -> bool:
        if self.should_run(message):
            logger.debug("Should run highlight, checking next command")
            if command_utility.matches(self.config["commands"]["highlight_all"], message):
                logger.debug("Highlighting all")
                self._highlight_all(room, message)
            elif command_utility.matches(self.config["commands"]["highlight_group"], message):
                logger.debug("Highlighting group")
                self._highlight_group(room, message)
            elif command_utility.matches(self.config["commands"]["highlight"], message):
                logger.debug("Highlighting")
                self._highlight(room, message)
            elif command_utility.matches(self.config["commands"]["add_to_group"], message):
                logger.debug("Adding to group")
                self._add_or_create_group(room, message)
            elif command_utility.matches(self.config["commands"]["delete_from_group"], message):
                logger.debug("Deleting from group")
                self._delete_from_group(room, message)
            else:
                raise RuntimeError("Could not find command to run on message, but should have been able to")
            return True
        return False

    def should_run(self, message) -> bool:
        if self.config.get("use_sqlite_database", False) and not self.config.get("sqlite_database_location"):
            logger.warning("Sqlite database location not set for Highlight module!")
            return False
        return command_utility.matches(self.config["commands"], message)

    def _highlight_all(self, room, message):
        users = room.get_joined_members()
        argument = command_utility.get_argument(message)
        online_user_ids = [user.user_id for user in
                           (filter(lambda user: self.matrix.is_online(user.user_id), users))]
        if online_user_ids:
            message = ", ".join(online_user_ids)
            logger.debug("Highlighting: {}".format(message))
            if argument:
                room.send_text(message + ": " + argument)
            else:
                room.send_text(message)
        else:
            logger.debug("No users to highlight in room {}".format(room.room_id))
            room.send_text("No online users to highlight")
        return

    def _highlight_group(self, room, message):
        arguments = command_utility.get_argument(message).split(None, 1)
        group = arguments[0]

        members = self._get_members(room, group)
        if members:
            members = ", ".join(members)
            logger.debug("Highlighting {}".format(members))
            if len(arguments) > 1:
                argument = arguments[1]
                room.send_text(members + ": " + argument)
            else:
                room.send_text(members)
        else:
            room.send_text("Group \"{}\" does not exist".format(group))
        return

    def _highlight(self, room, message):
        arguments = command_utility.get_argument(message).split(None, 1)
        group = arguments[0]
        members = self._get_members(room, group)
        member_user_ids = [self.matrix.get_user(room, member).user_id for member in members]
        members = list(filter(lambda user_id: self.matrix.is_online(user_id), member_user_ids))

        if members:
            members = ", ".join(members)

            if len(arguments) > 1:
                argument = arguments[1]
                room.send_text(members + ": " + argument)
            else:
                room.send_text(members)
        else:
            room.send_text("Group \"{}\" does not have any online members to highlight".format(group))

    def _add_or_create_group(self, room, message):
        arguments = command_utility.get_argument(message).split()
        group = arguments[0]
        users_to_add = arguments[1:]
        logger.debug("User wants to add {} to {}".format(users_to_add, group))
        if group and len(users_to_add) > 0:
            for user in users_to_add:
                if not self.matrix.get_user(room, user):
                    room.send_text("User: \"{}\" is not in room".format(user))
                    return

            new_members = []

            with self.database.connect() as conn:
                for user in users_to_add:
                    if self._is_in_group(conn, room.room_id, group, user):
                        logger.debug(
                            "User {} is already a member of group {} in room {}".format(user, group, room.room_id))
                    else:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT OR IGNORE INTO highlight_groups(ROOM_ID,GROUP_NAME,MEMBER) VALUES(?,?,?)",
                            (room.room_id, group, user))
                        conn.commit()
                        logger.debug("Inserted {} into group {} with id {}".format(user, group, cursor.lastrowid))
                        new_members.append(user)

            if new_members:
                room.send_text("Added \"{}\" to group \"{}\"".format(", ".join(new_members), group))
            else:
                room.send_text("Could not add \"{}\" to group \"{}\"".format(", ".join(users_to_add), group))
        else:
            room.send_text("Could not add: \"{}\" to group \"{}\". Syntax is incorrect".format(group, users_to_add))
        return

    def _delete_from_group(self, room, message):
        arguments = command_utility.get_argument(message).split()
        group = arguments[0]
        members_to_remove = arguments[1:]
        logger.debug("User wants to remove {} from {}".format(members_to_remove, group))
        if group and len(members_to_remove) > 0:
            for member in members_to_remove:
                if not self.matrix.get_user(room, member):
                    room.send_text("User: {} is not in room".format(member))
                    return

            removed_members = []
            with self.database.connect() as conn:
                for member in members_to_remove:
                    if self._is_in_group(conn, room.room_id, group, member):
                        cursor = conn.cursor()
                        cursor.execute(
                            "DELETE FROM highlight_groups WHERE room_id = ? AND group_name = ? and member = ?",
                            (room.room_id, group, member))
                        conn.commit()
                        removed_members.append(member)
            if removed_members:
                logger.debug(
                    "Removed {} from group {} in room {}".format(", ".join(removed_members), group, room.room_id))
                room.send_text("Removed \"{}\" from group \"{}\"".format(", ".join(removed_members), group))
            else:
                logger.debug(
                    "Could not remove {} from group {} in room {}".format(", ".join(members_to_remove), group,
                                                                          room.room_id))
                room.send_text("Could not remove \"{}\" from group \"{}\"".format(", ".join(members_to_remove), group))
        else:
            room.send_text(
                "Could not remove: \"{}\" from group \"{}\". Syntax is incorrect".format(group, members_to_remove))
        return

    @staticmethod
    def _is_in_group(conn, room_id, group, member) -> bool:
        first = conn.execute(
            "SELECT 1 FROM highlight_groups WHERE room_id = ? AND group_name = ? AND member = ? LIMIT 1",
            (room_id, group, member))
        result = first.fetchone()
        return result is not None

    def _get_members(self, room, group) -> list:
        return [row[0] for row in
                self.database.connect().execute(
                    "SELECT member FROM highlight_groups WHERE room_id = ? AND group_name = ?",
                    (room.room_id, group)).fetchall()]
