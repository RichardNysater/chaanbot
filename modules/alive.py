import logging

import command_utility

logger = logging.getLogger("ping")
config = {
    "always_run": False,
    "needs_init": False,
    "commands": ["!alive", "!running"]
}


def run(matrix_client, room, event, message) -> bool:
    if should_run(message):
        room.send_text("Yes.")
        return True
    return False


def should_run(message) -> bool:
    return command_utility.matches(config["commands"], message)
