#!/usr/bin/env python3

import configparser
import logging
import os
import sys
import traceback
from time import sleep

from matrix_client.client import MatrixClient

import scripts.alive

scripts = [
    {
        "name": "alive",
        "run_method": scripts.alive.run
    }
]

logger = logging.getLogger("chaanbot")


class Chaanbot():
    def __init__(self):
        try:
            root_path = os.path.dirname(os.path.realpath(__file__))
            self.config = configparser.ConfigParser()
            if "CONFIG" in os.environ:
                config_path = os.environ["CONFIG"]
            else:
                config_path = os.path.join(root_path, "chaanbot.cfg")
            logger.info("Reading config from {}".format(config_path))
            self.config.read(config_path)

            self.base_url = self.config.get("chaanbot", "matrix_server_url")
            self.token = self.config.get("chaanbot", "access_token")
            self.user_id = self.config.get("chaanbot", "user_id")
            self.connect()

            logger.info("Available rooms: " + str(list(self.client.rooms.keys())))
            listen_rooms = self.config.get("chaanbot", "listen_rooms", fallback=None)
            if listen_rooms:
                self.listen_rooms = [str.strip(room) for room in listen_rooms.split(",")]

            logger.info("Rooms to listen to: " + str(self.listen_rooms) + ". Will join these now.")
            for room_id in self.listen_rooms:
                self.join_room(room_id)

            allowed_inviters = self.config.get("chaanbot", "allowed_inviters", fallback=None)
            if allowed_inviters:
                self.allowed_inviters = [str.strip(inviter) for inviter in allowed_inviters.split(",")]
            self.load_scripts()

            self.client.add_invite_listener(self.on_invite)
            self.client.add_leave_listener(self.on_leave)
            self.client.start_listener_thread(exception_handler=lambda e: self.connect())

            while True:
                sleep(1)
        except Exception as exception:
            logger.exception("Failed with exception: " + str(exception), exception)

    def load_scripts(self):
        logger.info("Loading scripts")
        for script in scripts:
            try:
                script["config"] = {}
                if self.config.has_section(script["name"]):
                    for key, value in self.config.items(script["name"]):
                        script["config"]["__" + key] = value
                logger.info("Loaded script: {}".format(script["name"]))
            except Exception as e:
                logger.warning("Could not load script {} due to {}".format(script, str(e), e))

    def connect(self):
        try:
            logger.info("Connecting to {}".format(self.base_url))
            self.client = MatrixClient(self.base_url, token=self.token, user_id=self.user_id)
            logger.info("Connection successful")
        except Exception as e:
            logger.warning("Connection to {} failed".format(self.base_url) +
                           " with error message: " + str(e) + ", retrying in 5 seconds...")
            sleep(5)
            self.connect()

    def on_invite(self, room_id, state):
        sender = "Someone"
        for event in state["events"]:
            if event["type"] != "m.room.join_rules":
                continue
            sender = event["sender"]
            break

        logger.info("Invited to {} by {}".format(room_id, sender))
        try:
            for inviter in self.allowed_inviters:
                if inviter.lower() == sender.lower():
                    logger.info("{} is an approved inviter, attempting to join room".format(sender))
                    self.join_room(room_id)
                    return
            logger.info("{} is not an approved inviter, ignoring invite".format(sender))
            return
        except AttributeError:
            logger.info("Approved inviters turned off, attempting to join room: {}".format(room_id))
            self.join_room(room_id)

    def join_room(self, room_id):
        logger.info("Joining room: {}".format(room_id))
        room = self.client.join_room(room_id)
        room.add_listener(self.on_room_event)

    def on_leave(self, room_id, state):
        sender = "Someone"
        for event in state["timeline"]["events"]:
            if "membership" in event:
                continue
            sender = event["sender"]
        logger.info("Kicked from {} by {}".format(room_id, sender))

    def on_room_event(self, room, event):
        if event["sender"] == self.client.user_id:
            return
        if event["type"] != "m.room.message":
            return
        if event["content"]["msgtype"] != "m.text":
            return
        message = event["content"]["body"].strip()
        logger.debug("Running {} scripts on message".format(len(scripts)))
        for script in scripts:
            logger.debug("Running script {}".format(script["name"]))
            self.run_script(room, event, script, message)

    def run_script(self, room, event, script, args):
        logger.debug("Runnign script {}".format([script["name"], args]))
        script["run_method"](self, room, event, script, args)


if __name__ == "__main__":
    if "DEBUG" in os.environ:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    try:
        Chaanbot()
    except Exception:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)
