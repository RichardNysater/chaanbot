import logging
import re

logger = logging.getLogger("ping")
config = {
    "always_run": False,
    "commands": ["!alive", "!exists", "!running"]
}


def run(room, event, message) -> bool:
    if should_run(message):
        room.send_text("Yes.")
        return True
    return False


def should_run(message) -> bool:
    for command in config["commands"]:
        if re.search("^" + command + ".*", message, re.IGNORECASE):
            return True
    return False
