import os
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from chaanbot.modules.revamp import Revamp


class TestRevamp(IsolatedAsyncioTestCase):
    config_prefix_message = "prefix "

    def setUp(self) -> None:
        config = Mock()
        config.get.return_value = self.config_prefix_message
        self.event = Mock()
        self.event.sender = "user_id"
        self.room = AsyncMock()
        self.room.room_id = 1234
        self.matrix = AsyncMock()
        self.module = Revamp(config, self.matrix, Mock(), None)

    async def test_rewrite_amp(self):
        ran = await self.module.run(self.room, None, "Check this out: https://www.youtube.com/amp/6j6ksOu1231")

        self.assertFalse(ran)
        self.matrix.send_text_to_room.assert_any_call(
            self.config_prefix_message + "https://www.youtube.com/6j6ksOu1231",
            self.room.room_id)

    async def test_rewrite_several_amps(self):
        ran = await self.module.run(self.room, None,
                                    "Check these out: https://www.youtube.com/amp/6j6ksOu1231 "
                                    "and http://news.com/amp/russia-loses-ukraine-war great huh?")

        self.assertFalse(ran)
        self.matrix.send_text_to_room.assert_any_call(
            self.config_prefix_message + "https://www.youtube.com/6j6ksOu1231"
            + os.linesep + "http://news.com/russia-loses-ukraine-war",
            self.room.room_id)

    async def test_dont_rewrite_non_amp(self):
        ran = await self.module.run(self.room, None, "Check this out: https://www.news.com/amps/test")

        self.assertFalse(ran)
        self.matrix.send_text_to_room.assert_not_called()
