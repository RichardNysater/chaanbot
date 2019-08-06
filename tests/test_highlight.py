from unittest import TestCase
from unittest.mock import Mock

from modules import highlight


class TestHighlight(TestCase):

    def test_not_ran_if_wrong_command(self):
        room = Mock()
        ran = highlight.run(None, room, None, "highlight")
        self.assertFalse(ran)

    def test_config_has_properties(self):
        self.assertLess(0, len(highlight.config.get("commands")))
        self.assertFalse(highlight.config.get("always_run"))

    def test_should_run_returns_true_if_commands_match_and_sqlite_database_location_set(self):
        highlight.config["sqlite_database_location"] = "test"
        self.assertTrue(highlight.should_run("!hl group_to_highlight"))
        self.assertTrue(highlight.should_run("!highlight group_to_highlight"))

        self.assertTrue(highlight.should_run("!hla group person1 person2"))
        self.assertTrue(highlight.should_run("!hladd group person1 person2"))
        self.assertTrue(highlight.should_run("!highlightadd group person1 person2"))

        self.assertTrue(highlight.should_run("!hld group person1"))
        self.assertTrue(highlight.should_run("!hldelete group person1"))
        self.assertTrue(highlight.should_run("!highlightdelete group person1"))

        self.assertTrue(highlight.should_run("!hlg group"))
        self.assertTrue(highlight.should_run("!hlgroup group"))
        self.assertTrue(highlight.should_run("!highlightgroup group"))

        self.assertTrue(highlight.should_run("!hlall"))
        self.assertTrue(highlight.should_run("!hl all"))
        self.assertTrue(highlight.should_run("!highlightall"))
        self.assertTrue(highlight.should_run("!highlight all"))

    def test_should_not_run_if_no_sqlite_database_location(self):
        if highlight.config["use_sqlite_database"]:
            self.assertFalse(highlight.should_run("!hl group_to_highlight"))

    def test_should_run_returns_false_if_commands_do_not_match(self):
        self.assertFalse(highlight.should_run("highlight!"))
