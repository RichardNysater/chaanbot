""" The Alive module allows users to check if bot is alive

Available commands:
!alive                  - Bot will respond "Yes." if it's running and allowed to send to room.

Usage example:
!alive

Would results in:
"Bot: Yes."
"""
import logging

from chaanbot import command_utility

logger = logging.getLogger("ping")


class Alive:
    config = {
        "always_run": False,
        "operations": {
            "alive": {
                "commands": ["!alive", "!running"]
            }
        }
    }

    def run(self, room, event, message) -> bool:
        if self.should_run(message):
            room.send_text("Yes.")
            return True
        return False

    def should_run(self, message) -> bool:
        return command_utility.matches(self.config["operations"], message)
