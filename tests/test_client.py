from unittest import TestCase
from unittest.mock import Mock

from chaanbot.client import Client


class TestClient(TestCase):

    def get_config_side_effect(*args, **kwargs):
        if args[1] == "chaanbot":
            if args[2] == "modules_path":
                return ""
            elif args[2] == "allowed_inviters":
                return "allowed"
            elif args[2] == "blacklisted_room_ids":
                return "blacklisted"
            elif args[2] == "whitelisted_room_ids":
                return "whitelisted"
        return None

    def test_load_environment_on_initialization(self):
        module_runner = Mock()
        matrix = Mock()
        config = Mock()
        config.get.side_effect = self.get_config_side_effect

        self.client = Client(module_runner, config, matrix)

        config.get.assert_any_call("chaanbot", "allowed_inviters", fallback=None)
        config.get.assert_any_call("chaanbot", "blacklisted_room_ids", fallback=None)
        config.get.assert_any_call("chaanbot", "whitelisted_room_ids", fallback=None)

        self.assertEqual(["allowed"], self.client.allowed_inviters)
        self.assertEqual(["blacklisted"], self.client.blacklisted_room_ids)
        self.assertEqual(["whitelisted"], self.client.whitelisted_room_ids)
        self.assertEqual(matrix, self.client.matrix)
        self.assertEqual(config, self.client.config)
        pass

    def test_load_modules_on_initialization(self):
        pass  # TODO

    def test_join_rooms_and_add_listeners_when_ran(self):
        pass  # TODO: Figure out how to unit test the .run() method
