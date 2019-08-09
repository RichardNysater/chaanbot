import configparser
import logging
import os
import sys
import traceback
from time import sleep

from matrix_client.client import MatrixClient

from chaanbot import Chaanbot
from database import Database
from matrix import Matrix

logger = logging.getLogger("start")


def main():
    if "DEBUG" in os.environ:
        logger.info("Running in debug mode")
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    config_path = _get_config_path()
    logger.info("Reading config from {}".format(config_path))
    config = configparser.ConfigParser()
    if config.read(config_path):
        matrix_client = _connect(config)
        matrix = Matrix(matrix_client)
        database = Database(config.get("chaanbot", "sqlite_database_location", fallback=None))
        chaanbot = Chaanbot(config, matrix, database)
        chaanbot.run()
    else:
        logger.error("Could not read config file")


def _connect(config) -> MatrixClient:
    # Connect to a matrix server
    base_url = config.get("chaanbot", "matrix_server_url")
    token = config.get("chaanbot", "access_token")
    user_id = config.get("chaanbot", "user_id")
    try:
        logger.info("Connecting to {}".format(base_url))
        client = MatrixClient(base_url, token, user_id)
        logger.info("Connection successful")
        return client
    except Exception as e:
        logger.warning("Connection to {} failed".format(base_url) +
                       " with error message: " + str(e) + ", retrying in 5 seconds...")
        sleep(5)
        _connect(config)


def _get_config_path() -> str:
    if "CONFIG" in os.environ:
        return os.environ["CONFIG"]
    else:
        root_path = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(root_path, "chaanbot.cfg")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        logger.warning("Encountered exception {}.".format(str(e)), e)
        logger.info("Restarting bot")
        main()
    except Exception:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)
