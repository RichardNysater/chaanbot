from typing import Optional


def get_room_id(rooms, id_or_name_or_alias) -> str:
    """ Attempt to get a room id. Prio: room_id > canonical_alias > name > alias.
    Will not be able to get room_id if room is unlisted.
    """

    for room_id in rooms:
        room = rooms.get(room_id)
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


def get_user(room, user_id_or_display_name) -> Optional[str]:
    users = room.get_joined_members()
    for user in users:
        if (user_id_or_display_name.lower() == user.user_id.lower()) or (
                user_id_or_display_name.lower() == user.displayname.lower()):
            return user
    return None


def get_presence(matrix_client, user_id):
    """Returns an object like this:
    {
        "application/json": {
        "last_active_ago": 420845,
        "presence": "unavailable"
        }
    }
    """
    return matrix_client.api._send("GET", "/presence/" + user_id + "/status")
