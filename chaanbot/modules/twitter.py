""" The Twitter module will writes the text of a tweet in the chat by using Nitter.

Usage example:
MatrixUser
https://twitter.com/Twitter/status/1445078208190291973

Would result in:
"Bot: hello literally everyone"
"""
import logging
import re

from bs4 import BeautifulSoup
from nio import MatrixRoom, RoomMessage

from chaanbot.database import Database
from chaanbot.matrix import Matrix

logger = logging.getLogger("weather")


class Twitter:
    always_run = True  # Run on all messages, even if other modules has activated

    def __init__(self, config, matrix: Matrix, database: Database, requests):
        self.matrix = matrix
        self.requests = requests
        self.output_message_prefix = config.get("twitter", "prefix_message", fallback="Tweet body text:")

    async def run(self, room: MatrixRoom, event: RoomMessage, message) -> bool:
        links = re.findall(r"http[s]*://[w{3}.]*twitter\.com[^\s]+", message, re.IGNORECASE)
        links = [link.replace("twitter.com", "nitter.net") for link in links]
        texts = [self._getText(link) for link in links]
        if texts and all(texts):
            await self.matrix.send_text_to_room("\n".join([self.output_message_prefix + ' ' + link for link in texts]),
                                                room.room_id)

        return False  # The module does not use commands and should not return that it has handled one

    def _getText(self, link) -> str:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0'
        }
        response = self.requests.get(link, headers=headers)
        if response.status_code == 200:
            content = response.content
            soup = BeautifulSoup(content, 'html.parser')
            found = soup.find('div', {
                'class': 'tweet-content media-body'})
            if found:
                return found.get_text()
        return ""
