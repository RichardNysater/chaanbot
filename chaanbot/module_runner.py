import logging

from nio import MatrixRoom, RoomMessage

logger = logging.getLogger("module_runner")


class ModuleRunner:
    """ Responsible for running modules on messages in rooms """

    def __init__(self, config, matrix, module_loader):
        try:
            self.loaded_modules = module_loader.load_modules(config, matrix)
        except IOError as e:
            logger.warning("Could not load module(s) due to: {}".format(str(e)), e)

    async def run(self, event: RoomMessage, room: MatrixRoom, message):
        logger.debug("Running {} modules on message".format(len(self.loaded_modules)))
        for module in self.loaded_modules:
            await module.run(room, event, message)
