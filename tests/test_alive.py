from unittest import TestCase
from unittest.mock import Mock

from modules import alive


class TestAlive(TestCase):

    def test_send_alive_to_room(self):
        room = Mock()
        ran = alive.run(None, room, None, "!alive")
        self.assertTrue(ran)
        room.send_text.assert_any_call("Yes.")

    def test_not_ran_if_wrong_command(self):
        room = Mock()
        ran = alive.run(None, room, None, "alive")
        self.assertFalse(ran)
        room.send_text.assert_not_called()

    def test_config_has_properties(self):
        self.assertLess(0, len(alive.config.get("commands")))
        self.assertFalse(alive.config.get("always_run"))

    def test_should_run_returns_true_if_commands_match(self):
        self.assertTrue(alive.should_run("!alive"))
        self.assertTrue(alive.should_run("!running"))

    def test_should_run_returns_false_if_commands_do_not_match(self):
        self.assertFalse(alive.should_run("alive!"))
