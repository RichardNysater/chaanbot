from unittest import TestCase
from unittest.mock import Mock

import chaanbot


class TestChaanbot(TestCase):

    def get_config_side_effect(*args, **kwargs):
        if args[1] != "chaanbot":
            raise Exception("First argument is: {}, but should be: chaanbot".format(args[0]))
        if args[2] == "modules_path":
            return ""
        elif args[2] == "allowed_inviters":
            return "allowed"
        elif args[2] == "blacklisted_room_ids":
            return "blacklisted"
        elif args[2] == "whitelisted_room_ids":
            return "whitelisted"

    def test_load_environment_on_initialization(self):
        client = Mock()
        config = Mock()
        config.get.side_effect = self.get_config_side_effect

        self.chaanbot = chaanbot.Chaanbot(config, client)

        config.get.assert_any_call("chaanbot", "modules_path", fallback="modules")
        config.get.assert_any_call("chaanbot", "allowed_inviters", fallback=None)
        config.get.assert_any_call("chaanbot", "blacklisted_room_ids", fallback=None)
        config.get.assert_any_call("chaanbot", "whitelisted_room_ids", fallback=None)

        self.assertEquals(["allowed"], self.chaanbot.allowed_inviters)
        self.assertEquals(["blacklisted"], self.chaanbot.blacklisted_room_ids)
        self.assertEquals(["whitelisted"], self.chaanbot.whitelisted_room_ids)
        self.assertEquals(client, self.chaanbot.client)
        self.assertEquals(config, self.chaanbot.config)
        pass

    def test_load_modules_on_initialization(self):
        pass  # TODO

    def test_join_rooms_and_add_listeners_when_ran(self):
        pass  # TODO: Figure out how to unit test the .run() method
