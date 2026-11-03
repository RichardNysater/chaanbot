from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from chaanbot.module_loader import ModuleLoader


class TestModuleLoader(TestCase):
    def setUp(self):
        database = Mock()
        requests = Mock()
        config = Mock()
        config.get.return_value = None
        self.module_loader = ModuleLoader(config, database, requests)

    def test_load_enabled_and_disabled_config(self):
        database = Mock()
        requests = Mock()
        config = Mock()
        config.get.side_effect = self._get_config_side_effect_with_module1_disabled_and_module2_enabled
        module_loader = ModuleLoader(config, database, requests)
        self.assertEqual("module1", module_loader.disabled_modules[0])
        self.assertEqual("module2", module_loader.enabled_modules[0])

    def test_load_modules(self):
        files = ["module.py"]
        loaded_modules, import_module = self.mock_and_load_modules(files, self.module_loader)

        self.assertEqual(1, len(loaded_modules))
        import_module.assert_called_once()

    def test_load_subdirectory_modules(self):
        loaded_modules, import_module = self.mock_and_load_modules(
            ["subdirectory/module.py"], self.module_loader)
        self.assertEqual(1, len(loaded_modules))
        import_module.assert_called_once_with("chaanbot.modules.subdirectory.module")

    def test_dont_load_modules_with_wrong_filetype(self):
        files = ["module.pyc"]
        loaded_modules, import_module = self.mock_and_load_modules(files, self.module_loader)

        self.assertFalse(loaded_modules)
        import_module.assert_not_called()

    def test_dont_load_disabled_modules(self):
        database = Mock()
        requests = Mock()
        config = Mock()
        config.get.side_effect = self._get_config_side_effect_with_module_disabled
        module_loader = ModuleLoader(config, database, requests)

        files = ["module.py", "module2.py"]
        loaded_modules, import_module = self.mock_and_load_modules(files, module_loader)

        self.assertEqual(1, len(loaded_modules))
        import_module.assert_called_once()

    def test_only_load_enabled_modules(self):
        database = Mock()
        requests = Mock()
        config = Mock()
        config.get.side_effect = self._get_config_side_effect_with_module1_disabled_and_module2_enabled
        module_loader = ModuleLoader(config, database, requests)

        files = ["module.py", "module2.py", "module3.py"]
        loaded_modules, import_module = self.mock_and_load_modules(files, module_loader)

        self.assertEqual(1, len(loaded_modules))
        import_module.assert_called_once()

    @staticmethod
    def mock_and_load_modules(files, module_loader):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in files:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            with patch("chaanbot.module_loader.resources.files", return_value=root):
                with patch("importlib.import_module") as import_module:
                    loaded_modules = module_loader.load_modules(Mock(), Mock())
        return loaded_modules, import_module

    def _get_config_side_effect_with_module1_disabled_and_module2_enabled(*args, **kwargs):
        if args[1] == "modules":
            if args[2] == "disabled":
                return "module1"
            elif args[2] == "enabled":
                return "module2"
        return None

    def _get_config_side_effect_with_module_disabled(*args, **kwargs):
        if args[1] == "modules":
            if args[2] == "disabled":
                return "module"
        return None
