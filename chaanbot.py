#!/usr/bin/env python3

import importlib
import logging
import os
from time import sleep

logger = logging.getLogger("chaanbot")


class Chaanbot:
    blacklisted_room_ids, whitelisted_room_ids, loaded_modules, allowed_inviters = [], [], [], []

    def __init__(self, config, matrix_client):
        try:
            try:
                self.__load_modules(config)
            except IOError as e:
                logger.warning("Could not load module(s) due to: {}".format(str(e)), e)
            self.__load_environment(config)
            self.config = config
            self.client = matrix_client
            logger.info("Chaanbot successfully initialized.")

        except Exception as exception:
            logger.exception("Failed with exception: {}".format(str(exception)), exception)
            raise exception

    def run(self):
        self.__join_rooms(self.config)
        self.client.add_invite_listener(self.__on_invite)
        self.client.add_leave_listener(self.__on_leave)
        self.client.start_listener_thread()
        logger.info("Listeners added, now running...")
        while True:
            sleep(1)

    def __load_environment(self, config):
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

    def __load_modules(self, config):
        scripts_path = config.get("chaanbot", "modules_path", fallback="modules")

        files = os.listdir(scripts_path)
        logger.info("Loading modules: {}".format(files))

        for file in files:
            if '.py' in file:
                module_name = file.replace('.py', '')
                logger.debug("Importing module: {}".format(module_name))
                module = importlib.import_module("modules." + module_name)
                module.config["always_run"] = module.config.get("always_run", False)
                self.loaded_modules.append(module)

    def __join_rooms(self, config):
        logger.debug("Available rooms: " + str(list(self.client.rooms.keys())))
        if config.has_option("chaanbot", "listen_rooms"):
            listen_rooms = [str.strip(room) for room in
                            config.get("chaanbot", "listen_rooms", fallback=None).split(",")]
            logger.info("Rooms to listen to: " + str(listen_rooms) + ". Will attempt to join these now.")
            for room_id in listen_rooms:
                self.__join_room(room_id)

        for room_id in self.client.rooms:
            if self.client.rooms.get(room_id).invite_only:
                logger.info(
                    "Private room detected, will attempt to join it: {}".format(room_id))
                self.__join_room(room_id)

    def __on_invite(self, room_id, state):
        sender = "Someone"
        for event in state["events"]:
            if event["type"] == "m.room.member" and event["content"]["membership"] == "invite" and \
                    event["state_key"] == self.client.user_id:
                sender = event["sender"]
                break

        logger.info("Invited to {} by {}".format(room_id, sender))
        try:
            for inviter in self.allowed_inviters:
                if inviter.lower() == sender.lower():
                    logger.info("{} is an approved inviter, attempting to join room".format(sender))
                    self.__join_room(room_id)
                    return
            logger.info("{} is not an approved inviter, ignoring invite".format(sender))
            return
        except AttributeError:
            logger.info("Approved inviters turned off, attempting to join room: {}".format(room_id))
            self.__join_room(room_id)

    def __join_room(self, room_id_or_alias):
        room_id = self.__get_room_id(room_id_or_alias)
        room_id = room_id if room_id else room_id_or_alias  # Might not be able to get room_id if room was unlisted
        if self.whitelisted_room_ids:
            for whitelisted_room_id_or_alias in self.whitelisted_room_ids:
                whitelisted_room_id = self.__get_room_id(whitelisted_room_id_or_alias)
                if whitelisted_room_id == room_id:
                    logger.info("Room {} is whitelisted, joining it".format(room_id_or_alias))
                    room = self.client.join_room(whitelisted_room_id_or_alias)
                    room.add_listener(self.__on_room_event)
            logger.info("Room {} is not whitelisted, will not join it".format(room_id_or_alias))
        elif self.blacklisted_room_ids:
            for blacklisted_room_id_or_alias in self.blacklisted_room_ids:
                blacklisted_room_id = self.__get_room_id(blacklisted_room_id_or_alias)
                if blacklisted_room_id == room_id:
                    logger.info("Room {} is blacklisted, will not join it".format(blacklisted_room_id_or_alias))
                    return
            logger.info("Room {} is not blacklisted, will join it".format(room_id_or_alias))
            room = self.client.join_room(room_id_or_alias)
            room.add_listener(self.__on_room_event)
        else:
            logger.info("Joining room {}".format(room_id_or_alias))
            room = self.client.join_room(room_id_or_alias)
            room.add_listener(self.__on_room_event)

    def __on_room_event(self, room, event):
        if event["sender"] == self.client.user_id:
            return
        if event["type"] != "m.room.message":
            return
        if event["content"]["msgtype"] != "m.text":
            return
        message = event["content"]["body"].strip()
        self.__run_modules(event, room, message)

    def __run_modules(self, event, room, message):
        logger.info("Running {} modules on message".format(len(self.loaded_modules)))
        module_processed_message = False
        for module in self.loaded_modules:
            if not module_processed_message or module.config["always_run"]:
                logger.debug("Running module {}".format(module))
                if module.run(room, event, message):
                    module_processed_message = True
                    logger.debug("Module processed message successfully")
            else:
                logger.debug("Module {} did not run as another module has already processed message".format(module))

    def __get_room_id(self, id_or_name_or_alias) -> str:
        """ Attempt to get a room id. Prio: room_id > canonical_alias > name > alias.
        Will not be able to get room_id if room is unlisted.
        """

        for room_id in self.client.rooms:
            room = self.client.rooms.get(room_id)
            if room.room_id == id_or_name_or_alias:
                return room

        for room_id in self.client.rooms:
            room = self.client.rooms.get(room_id)
            if room.canonical_alias == id_or_name_or_alias:
                return room

        for room_id in self.client.rooms:
            room = self.client.rooms.get(room_id)
            if room.name == id_or_name_or_alias:
                return room

        for room_id in self.client.rooms:
            room = self.client.rooms.get(room_id)
            if id_or_name_or_alias in room.aliases:
                return room

    @staticmethod
    def __on_leave(room_id, state):
        sender = "Someone"
        for event in state["timeline"]["events"]:
            if "membership" in event:
                continue
            sender = event["sender"]
        logger.info("Kicked or disinvited from {} by {}".format(room_id, sender))
