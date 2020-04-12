from unittest import TestCase
from unittest.mock import Mock

from chaanbot.module_runner import ModuleRunner


class TestModuleRunner(TestCase):

    def test_loads_modules_on_init(self):
        config = Mock()
        matrix = Mock()

        modules = ["modules"]
        module_loader = Mock()
        module_loader.load_modules.return_value = modules
        module_runner = ModuleRunner(config, matrix, module_loader)
        self.assertEqual(modules, module_runner.loaded_modules)

    def test_runs_loaded_modules(self):
        module1 = Mock()
        module1.run.return_value = False
        module2 = Mock()
        module2.run.return_value = False

        modules = [module1, module2]

        self.run_module_loader(modules)

        module1.run.assert_called_once()
        module2.run.assert_called_once()

    def test_stops_running_modules_on_True_return(self):
        module1 = Mock()
        module1.always_run = None
        module1.run.return_value = True
        module2 = Mock()
        module2.always_run = None
        module2.run.return_value = False

        modules = [module1, module2]

        self.run_module_loader(modules)

        module1.run.assert_called_once()
        module2.run.assert_not_called()

    def test_always_run_modules_with_always_run_True(self):
        module1 = Mock()
        module1.always_run = None
        module1.run.return_value = True
        module2 = Mock()
        module2.always_run = True
        module2.run.return_value = False

        modules = [module1, module2]

        self.run_module_loader(modules)

        module1.run.assert_called_once()
        module2.run.assert_called_once()

    def run_module_loader(self, modules):
        config = Mock()
        matrix = Mock()

        module_loader = Mock()
        module_loader.load_modules.return_value = modules
        module_runner = ModuleRunner(config, matrix, module_loader)
        event = Mock()
        room = Mock()
        message = Mock()
        module_runner.run(event, room, message)
