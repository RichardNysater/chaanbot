from unittest import TestCase

import command_utility


class TestCommandUtility(TestCase):

    def test_match_dict_input(self):
        commands = {"commands": ["cmd1", "cmd2"]}
        self.assertTrue(command_utility.matches(commands, "cmd1"))
        self.assertTrue(command_utility.matches(commands, "cmd2"))

    def test_match_list_input(self):
        commands = ["cmd1", "cmd2"]
        self.assertTrue(command_utility.matches(commands, "cmd1"))
        self.assertTrue(command_utility.matches(commands, "cmd2"))

    def test_not_match_dict_input(self):
        commands = {"commands": ["cmd1", "cmd2"]}
        self.assertFalse(command_utility.matches(commands, "commands"))  # Should not match dict key
        self.assertFalse(command_utility.matches(commands, "cmd"))  # Should not partial match
        self.assertFalse(command_utility.matches(commands, "cmd11"))  # Should not match longer
        self.assertFalse(command_utility.matches(commands, None))  # Should not match None
        self.assertFalse(command_utility.matches(None, "cmd2"))  # Should not match None

    def test_not_match_list_input(self):
        commands = ["cmd1", "cmd2"]
        self.assertFalse(command_utility.matches(commands, "cmd"))  # Should not partial match
        self.assertFalse(command_utility.matches(commands, "cmd11"))  # Should not match longer
        self.assertFalse(command_utility.matches(commands, None))  # Should not match None
        self.assertFalse(command_utility.matches(None, "cmd2"))  # Should not match None

    def test_get_command_and_argument(self):
        expected_command = "!command"
        expected_argument = "argument for command"
        message = expected_command + " " + expected_argument
        (command, argument) = command_utility.get_command_and_argument(message)
        self.assertEqual(expected_command, command)
        self.assertEqual(expected_argument, argument)
        self.assertEqual(expected_command, command_utility.get_command(message))
        self.assertEqual(expected_argument, command_utility.get_argument(message))
