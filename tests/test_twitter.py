from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from chaanbot.modules.twitter import Twitter


class TestTwitter(IsolatedAsyncioTestCase):
    config_prefix_message = "prefix"
    config_prefix_message_output = config_prefix_message + ' '

    def setUp(self) -> None:
        config = Mock()
        config.get.return_value = self.config_prefix_message
        self.event = Mock()
        self.event.sender = "user_id"
        self.requests = Mock()
        self.room = AsyncMock()
        self.room.room_id = 1234
        self.matrix = AsyncMock()
        self.module = Twitter(config, self.matrix, Mock(), self.requests)

    async def test_fetch_twitter(self):
        tweet_text = "hello literally everyone"
        response = Mock()
        response.status_code = 200
        response.content = '<html><div class="tweet-content media-body" dir="auto">' + tweet_text + '</div></html>'
        self.requests.get.return_value = response

        ran = await self.module.run(self.room, None,
                                    "Check this out: https://twitter.com/Twitter/status/1445078208190291973")

        self.assertFalse(ran)
        self.matrix.send_text_to_room.assert_any_call(
            self.config_prefix_message_output + tweet_text,
            self.room.room_id)

    async def test_fetch_several_tweets(self):
        tweet_text = "hello literally everyone"
        response = Mock()
        response.status_code = 200
        response.content = '<html><div class="tweet-content media-body" dir="auto">' + tweet_text + '</div></html>'
        self.requests.get.return_value = response

        ran = await self.module.run(self.room, None,
                                    "Check this out: https://twitter.com/Twitter/status/1445078208190291973 and https://twitter.com/Twitter/status/1445078208190291972")

        self.assertFalse(ran)
        self.matrix.send_text_to_room.assert_any_call(
            self.config_prefix_message_output + tweet_text + "\n" + self.config_prefix_message_output + tweet_text,
            self.room.room_id)

    async def test_handle_404(self):
        response = Mock()
        response.status_code = 404
        self.requests.get.return_value = response

        ran = await self.module.run(self.room, None,
                                    "Check this out: https://twitter.com/Twitter/status/1445078208190291973")

        self.assertFalse(ran)
        self.requests.get.assert_called()
        self.matrix.send_text_to_room.assert_not_called()

    async def test_handle_not_finding_tweet(self):
        response = Mock()
        response.status_code = 200
        response.content = '<html><div class="tweest-content medias-body" dir="auto"></div></html>'
        self.requests.get.return_value = response

        ran = await self.module.run(self.room, None,
                                    "Check this out: https://twitter.com/Twitter/status/1445078208190291973")

        self.assertFalse(ran)
        self.matrix.send_text_to_room.assert_not_called()
