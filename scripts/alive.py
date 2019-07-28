import logging
import re

logger = logging.getLogger("ping")

commands = {
    "!alive", "!exists", "!running"
}


def run(self, room, event, script, message):
    if should_run(message):
        room.send_text("Yes.")


def should_run(message):
    for command in commands:
        if re.search("^" + command + ".*", message, re.IGNORECASE):
            return True
    return False
