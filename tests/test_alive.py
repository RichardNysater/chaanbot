from unittest import TestCase
from unittest.mock import Mock

from chaanbot.modules.alive import Alive


class TestAlive(TestCase):

    def test_send_alive_to_room(self):
        room = Mock()
        ran = Alive().run(room, None, "!alive")
        self.assertTrue(ran)
        room.send_text.assert_any_call("Yes.")

    def test_not_ran_if_wrong_command(self):
        room = Mock()
        ran = Alive().run(room, None, "alive")
        self.assertFalse(ran)
        room.send_text.assert_not_called()

    def test_config_has_properties(self):
        alive_class = Alive()
        self.assertLess(0, len(alive_class.config.get("operations")))
        self.assertFalse(alive_class.config.get("always_run"))

    def test_should_run_returns_true_if_commands_match(self):
        alive_class = Alive()
        self.assertTrue(alive_class.should_run("!alive"))
        self.assertTrue(alive_class.should_run("!running"))

    def test_should_run_returns_false_if_commands_do_not_match(self):
        alive_class = Alive()
        self.assertFalse(alive_class.should_run("alive!"))
