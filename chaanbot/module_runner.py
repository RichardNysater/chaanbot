import logging

logger = logging.getLogger("module_runner")


class ModuleRunner:
    """ Responsible for running modules on messages in rooms """

    def __init__(self, config, matrix, module_loader):
        try:
            self.loaded_modules = module_loader.load_modules(config, matrix)
        except IOError as e:
            logger.warning("Could not load module(s) due to: {}".format(str(e)), e)

    def run(self, event, room, message):
        logger.info("Running {} modules on message".format(len(self.loaded_modules)))
        module_processed_message = False
        for module in self.loaded_modules:
            if not module_processed_message or module.always_run:
                logger.debug("Running module {}".format(module))
                if module.run(room, event, message):
                    module_processed_message = True
                    logger.debug("Module processed message successfully")
            else:
                logger.debug("Module {} did not run as another module has already processed message".format(module))
