import logging
from typing import Optional

logger = logging.getLogger("matrix_utility")


class Matrix:
    def __init__(self, matrix_client):
        self.matrix_client = matrix_client

    def get_room(self, rooms, id_or_name_or_alias) -> Optional[str]:
        """ Attempt to get a room. Prio: room_id > canonical_alias > name > alias.
        Will not be able to get room if not in room
        """

        for room in rooms.values():
            if room.room_id == id_or_name_or_alias:
                return room

        for room_id in rooms:
            room = rooms.get(room_id)
            if room.canonical_alias == id_or_name_or_alias:
                return room

        for room_id in rooms:
            room = rooms.get(room_id)
            if room.name == id_or_name_or_alias:
                return room

        for room_id in rooms:
            room = rooms.get(room_id)
            if id_or_name_or_alias in room.aliases:
                return room
        return None

    def get_user(self, room, user_id_or_display_name) -> Optional[str]:
        users = room.get_joined_members()
        for user in users:
            if (user_id_or_display_name.lower() == user.user_id.lower()) or (
                    user_id_or_display_name.lower() == user.displayname.lower()):
                return user
        return None

    def is_online(self, user_id):
        presence = self.get_presence(user_id)
        logger.debug("presence: {}".format(presence))
        return presence["presence"] == "online"

    def get_presence(self, user_id):
        """Returns an object like this:
        {
            "application/json": {
            "last_active_ago": 420845,
            "presence": "unavailable"
            }
        }
        """
        return self.matrix_client.api._send("GET", "/presence/" + user_id + "/status")
