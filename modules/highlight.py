import logging
import sqlite3

import command_utility
import matrix_utility

logger = logging.getLogger("highlight")
config = {
    "always_run": False,
    "needs_init": True,
    "commands": {"highlight_all": ["!hlall", "!highlightall"],
                 "highlight_group": ["!hlg", "!highlightgroup", "!hlgroup"],
                 "add_to_group": ["!hla", "!hladd", "!highlightadd"],
                 "delete_from_group": ["!hld", "!hldelete", "!highlightdelete"],
                 "highlight": ["!hl", "!highlight"]},
    "use_sqlite_database": True,
    "sqlite_database_location": None  # Should be set by main script on load
}


def init():
    conn, _ = __connect_to_database()
    logger.debug("Initializing highlight database")
    conn.execute('''CREATE TABLE IF NOT EXISTS highlight_groups
    (ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    ROOM_ID TEXT NOT NULL,
    "GROUP_NAME" TEXT NOT NULL,
    MEMBER TEXT NOT NULL,
    UNIQUE(ROOM_ID,GROUP_NAME,MEMBER));    
    ''')


def run(matrix_client, room, event, message) -> bool:
    if should_run(message):
        logger.debug("Should run highlight, checking next command")
        if command_utility.matches(config["commands"]["highlight_all"], message):
            logger.debug("Highlighting all")
            __highlight_all(matrix_client, room)
        elif command_utility.matches(config["commands"]["highlight_group"], message):
            logger.debug("Highlighting group")
            __highlight_group(room, message)
        elif command_utility.matches(config["commands"]["highlight"], message):
            logger.debug("Highlighting")
            __highlight(matrix_client, room, message)
        elif command_utility.matches(config["commands"]["add_to_group"], message):
            logger.debug("Adding to group")
            __add_or_create_group(room, message)
        elif command_utility.matches(config["commands"]["delete_from_group"], message):
            logger.debug("Deleting from group")
            __delete_from_group(room, message)
        else:
            raise RuntimeError("Could not find command to run on message, but should have been able to.")
        return True
    return False


def should_run(message) -> bool:
    if config.get("use_sqlite_database", False) and not config.get("sqlite_database_location"):
        logger.warning("Sqlite database location not set for Highlight module!")
        return False
    return command_utility.matches(config["commands"], message)


def __highlight_all(matrix_client, room):
    users = room.get_joined_members()
    online_user_ids = [user.user_id for user in (filter(lambda user: __is_online(matrix_client, user.user_id), users))]
    message = ", ".join(online_user_ids)
    logger.info("Highlighting: {}".format(message))
    room.send_text(message)
    return


def __highlight_group(room, message):
    argument = command_utility.get_argument(message)
    group = argument

    members = __get_members(room, group)
    members = ",".join(members)
    logger.debug("Highlighting {}".format(members))
    room.send_text(members)
    return


def __highlight(matrix_client, room, message):
    arguments = command_utility.get_argument(message).split(None, 1)
    group = arguments[0]
    members = __get_members(room, group)
    member_user_ids = [matrix_utility.get_user(room, member).user_id for member in members]
    members = list(filter(lambda user_id: __is_online(matrix_client, user_id), member_user_ids))
    members = ",".join(members)

    if len(arguments) > 1:
        argument = arguments[1]
        room.send_text(members + ": " + argument)
    else:
        room.send_text(members)
    return


def __is_online(matrix_client, user_id):
    presence = matrix_utility.get_presence(matrix_client, user_id)
    logger.debug("presence: {}".format(presence))
    return presence["presence"] == "online"


def __add_or_create_group(room, message):
    arguments = command_utility.get_argument(message).split()
    group = arguments[0]
    new_members = arguments[1:]
    logger.debug("User wants to add {} to {}".format(new_members, group))
    if group and len(new_members) > 0:
        for member in new_members:
            if not matrix_utility.get_user(room, member):
                room.send_text("User: {} is not in room.".format(member))
                return

        _, cursor = __connect_to_database()
        for member in new_members:
            cursor.execute("INSERT INTO highlight_groups(ROOM_ID,GROUP_NAME,MEMBER) VALUES(?,?,?)",
                           (room.room_id, group, member))
            logger.info("Inserted {} into group {} with id {}".format(member, group, cursor.lastrowid))
        room.send_text("Added {} to group {}.".format(",".join(new_members), group))
    else:
        room.send_text("Attempted to add: {}, to group {}. Syntax is incorrect".format(group, new_members))
    return


def __delete_from_group(room, message):
    arguments = command_utility.get_argument(message).split()
    group = arguments[0]
    members_to_remove = arguments[1:]
    logger.debug("User wants to remove {} from {}".format(members_to_remove, group))
    if group and len(members_to_remove) > 0:
        for member in members_to_remove:
            if not matrix_utility.get_user(room, member):
                room.send_text("User: {} is not in room.".format(member))
                return

        _, cursor = __connect_to_database()
        for member in members_to_remove:
            cursor.execute("DELETE FROM highlight_groups WHERE room_id = ? AND group_name = ? and member = ?",
                           (room.room_id, group, member))
            logger.info("Removed {} from group {} in room {}".format(member, group, room.room_id))
        room.send_text("Removed {} from group {}.".format(",".join(members_to_remove), group))
    else:
        room.send_text("Attempted to remove: {} from group {}. Syntax is incorrect".format(group, members_to_remove))
    return


def __get_members(room, group) -> list:
    conn, _ = __connect_to_database()
    return [row[0] for row in conn.execute("SELECT member FROM highlight_groups WHERE room_id = ? AND group_name = ?",
                                           (room.room_id, group)).fetchall()]


def __connect_to_database():
    conn = sqlite3.connect(config.get("sqlite_database_location"), isolation_level=None)
    cursor = conn.cursor()
    return conn, cursor
