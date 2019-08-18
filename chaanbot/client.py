#!/usr/bin/env python3

import logging
from time import sleep

logger = logging.getLogger("chaanbot")


class Client:
    """ Main class for the bot. The client receives messages, joins rooms etc. """

    blacklisted_room_ids, whitelisted_room_ids, loaded_modules, allowed_inviters = [], [], [], []

    def __init__(self, module_runner, config, matrix):
        try:
            self._load_environment(config)
            self.module_runner = module_runner
            self.config = config
            self.matrix = matrix
            logger.info("Chaanbot successfully initialized.")

        except Exception as exception:
            logger.exception("Failed with exception: {}".format(str(exception)), exception)
            raise exception

    def run(self, exception_handler):
        self._join_rooms(self.config)
        self.matrix.matrix_client.add_invite_listener(self._on_invite)
        self.matrix.matrix_client.add_leave_listener(self._on_leave)
        self.matrix.matrix_client.start_listener_thread(exception_handler=exception_handler)
        logger.info("Listeners added, now running...")
        while True:
            sleep(1)

    def _load_environment(self, config):
        allowed_inviters = config.get("chaanbot", "allowed_inviters", fallback=None)
        if allowed_inviters:
            self.allowed_inviters = [str.strip(inviter) for inviter in allowed_inviters.split(",")]
            logger.debug("Allowed inviters: {}".format(self.allowed_inviters))

        blacklisted_rooms = config.get("chaanbot", "blacklisted_room_ids", fallback=None)
        if blacklisted_rooms:
            self.blacklisted_room_ids = [str.strip(room) for room in blacklisted_rooms.split(",")]
            logger.debug("Blacklisted rooms: {}".format(self.blacklisted_room_ids))

        whitelisted_rooms = config.get("chaanbot", "whitelisted_room_ids", fallback=None)
        if whitelisted_rooms:
            self.whitelisted_room_ids = [str.strip(room) for room in whitelisted_rooms.split(",")]
            logger.debug("Whitelisted rooms: {}".format(self.whitelisted_room_ids))

    def _join_rooms(self, config):
        logger.debug("Available rooms: " + str(list(self.matrix.matrix_client.rooms.keys())))
        if config.has_option("chaanbot", "listen_rooms"):
            listen_rooms = [str.strip(room) for room in
                            config.get("chaanbot", "listen_rooms", fallback=None).split(",")]
            logger.info("Rooms to listen to: " + str(listen_rooms) + ". Will attempt to join these now.")
            for room_id in listen_rooms:
                self._join_room(room_id)

        for room_id in self.matrix.matrix_client.rooms:
            if self.matrix.matrix_client.rooms.get(room_id).invite_only:
                logger.info(
                    "Private room detected, will attempt to join it: {}".format(room_id))
                self._join_room(room_id)

    def _on_invite(self, room_id, state):
        sender = "Someone"
        for event in state["events"]:
            if event["type"] == "m.room.member" and event["content"]["membership"] == "invite" and \
                    event["state_key"] == self.matrix.matrix_client.user_id:
                sender = event["sender"]
                break

        logger.info("Invited to {} by {}".format(room_id, sender))
        try:
            for inviter in self.allowed_inviters:
                if inviter.lower() == sender.lower():
                    logger.info("{} is an approved inviter, attempting to join room".format(sender))
                    self._join_room(room_id)
                    return
            logger.info("{} is not an approved inviter, ignoring invite".format(sender))
            return
        except AttributeError:
            logger.info("Approved inviters turned off, attempting to join room: {}".format(room_id))
            self._join_room(room_id)

    def _join_room(self, room_id_or_alias):
        room = self.matrix.get_room(self.matrix.matrix_client.rooms, room_id_or_alias)
        room_id = room.room_id if room else room_id_or_alias  # Might not be able to get room_id if room was unlisted
        if self.whitelisted_room_ids:
            for whitelisted_room_id_or_alias in self.whitelisted_room_ids:
                whitelisted_room = self.matrix.get_room(self.matrix.matrix_client.rooms, whitelisted_room_id_or_alias)
                if whitelisted_room and whitelisted_room.room_id == room_id:
                    logger.info("Room {} is whitelisted, joining it".format(room_id_or_alias))
                    room = self.matrix.matrix_client.join_room(whitelisted_room_id_or_alias)
                    room.add_listener(self._on_room_event)
            logger.info("Room {} is not whitelisted, will not join it".format(room_id_or_alias))
        elif self.blacklisted_room_ids:
            for blacklisted_room_id_or_alias in self.blacklisted_room_ids:
                blacklisted_room = self.matrix.get_room(self.matrix.matrix_client.rooms, blacklisted_room_id_or_alias)
                if blacklisted_room and blacklisted_room.room_id == room_id:
                    logger.info("Room {} is blacklisted, will not join it".format(blacklisted_room_id_or_alias))
                    return
            logger.info("Room {} is not blacklisted, will join it".format(room_id_or_alias))
            room = self.matrix.matrix_client.join_room(room_id_or_alias)
            room.add_listener(self._on_room_event)
        else:
            logger.info("Joining room {}".format(room_id_or_alias))
            room = self.matrix.matrix_client.join_room(room_id_or_alias)
            room.add_listener(self._on_room_event)

    def _on_room_event(self, room, event):
        if event["sender"] == self.matrix.matrix_client.user_id:
            return
        if event["type"] != "m.room.message":
            return
        if event["content"]["msgtype"] != "m.text":
            return
        message = event["content"]["body"].strip()
        self.module_runner.run(event, room, message)

    @staticmethod
    def _on_leave(room_id, state):
        sender = "Someone"
        for event in state["timeline"]["events"]:
            if "membership" in event:
                continue
            sender = event["sender"]
        logger.info("Kicked or disinvited from {} by {}".format(room_id, sender))
