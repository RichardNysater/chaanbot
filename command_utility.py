import logging
from typing import Optional

logger = logging.getLogger("command_utility")


def matches(commands_dict_or_list, message) -> bool:
    if not message:
        return False

    if isinstance(commands_dict_or_list, dict):
        for operation in commands_dict_or_list:
            for command in commands_dict_or_list[operation]:
                if command and command.lower() == get_command_and_argument(message)[0].lower():
                    logger.debug("Message matches command dict")
                    return True
    elif isinstance(commands_dict_or_list, list):
        for command in commands_dict_or_list:
            if command and command.lower() == get_command_and_argument(message)[0].lower():
                logger.debug("Message matches command list")
                return True
    return False


def get_command(message) -> str:
    return get_command_and_argument(message)[0]


def get_argument(message) -> Optional[str]:
    try:
        return get_command_and_argument(message)[1]
    except IndexError:
        return None


def get_command_and_argument(message) -> (str, str):
    return message.split(None, 1)
