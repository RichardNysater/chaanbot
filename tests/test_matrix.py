from unittest import mock, IsolatedAsyncioTestCase
from unittest.mock import Mock

from chaanbot.matrix import Matrix


class TestMatrixUtility(IsolatedAsyncioTestCase):
    def setUp(self):
        config = Mock()
        config.get.return_value = None
        matrix_client = Mock()
        self.matrix = Matrix(config, matrix_client)

    def test_initialize_black_and_whitelisted_rooms(self):
        config = Mock()
        config.get.side_effect = self._get_config_side_effect
        matrix_client = Mock()
        matrix = Matrix(config, matrix_client)
        self.assertEqual(["whitelisted"], matrix.whitelisted_room_ids)
        self.assertEqual(["blacklisted"], matrix.blacklisted_room_ids)

    def _get_config_side_effect(*args, **kwargs):
        if args[1] == "chaanbot":
            if args[2] == "blacklisted_room_ids":
                return "blacklisted"
            elif args[2] == "whitelisted_room_ids":
                return "whitelisted"
        return None

    def test_get_room_by_room_id(self):
        room_id = "id"
        mocked_room = Mock()
        mocked_room.room_id = room_id

        rooms = {"123123": mocked_room}

        actual_room = self.matrix.get_room(rooms, room_id)

        self.assertEqual(mocked_room, actual_room)

    def test_get_room_by_canonical_alias(self):
        canonical_alias = "alias"
        mocked_room = Mock()
        mocked_room.canonical_alias = canonical_alias

        rooms = {"123123": mocked_room}

        actual_room = self.matrix.get_room(rooms, canonical_alias)

        self.assertEqual(mocked_room, actual_room)

    def test_get_room_by_name(self):
        name = "name"
        mocked_room = Mock()
        mocked_room.name = name

        rooms = {"123123": mocked_room}

        actual_room = self.matrix.get_room(rooms, name)

        self.assertEqual(mocked_room, actual_room)

    def test_dont_get_room_if_no_match(self):
        mocked_room = Mock()
        mocked_room.aliases = ["no"]
        mocked_room.name = "no"
        mocked_room.canonical_alias = "no"
        mocked_room.room_id = "no"

        rooms = {"123123": mocked_room}

        actual_room = self.matrix.get_room(rooms, "yes!")

        self.assertIsNone(actual_room)

    def test_get_user_by_id(self):
        user_id = "user"
        mocked_room = mock.Mock()
        mocked_user = mock.Mock()

        mocked_room.users = {"doesntmatter": mocked_user}
        mocked_user.user_id = user_id

        actual_user = self.matrix.get_user(mocked_room, user_id)

        self.assertEqual(mocked_user, actual_user)

    def test_get_user_by_display_name(self):
        display_name = "displayname"
        mocked_room = mock.Mock()
        mocked_user = mock.Mock()

        mocked_room.users = {"doesntmatter": mocked_user}
        mocked_user.display_name = display_name

        actual_user = self.matrix.get_user(mocked_room, display_name)

        self.assertEqual(mocked_user, actual_user)

    def test_dont_get_user_if_no_match(self):
        display_name = "displayname"
        user_id = "user"
        mocked_room = mock.Mock()
        mocked_user = mock.Mock()

        mocked_room.users = {"doesntmatter": mocked_user}
        mocked_user.display_name = display_name
        mocked_user.user_id = user_id

        actual_user = self.matrix.get_user(mocked_room, "neither")

        self.assertIsNone(actual_user)

    def test_get_presence(self):
        expected_presence = "presence"
        user_id = "user"
        room_id = "room"
        self._mock_get_presence(expected_presence, room_id, user_id)

        actual_presence = self.matrix.get_presence(room_id, user_id)

        self.assertEqual(expected_presence, actual_presence)

    def test_user_online_if_presence_is_online(self):
        expected_presence = "online"
        user_id = "user"
        room_id = "room"
        self._mock_get_presence(expected_presence, room_id, user_id)

        online = self.matrix.is_online(room_id, user_id)

        self.assertTrue(online)

    def test_user_not_online_if_presence_is_offline(self):
        expected_presence = "offline"
        user_id = "user"
        room_id = "room"
        self._mock_get_presence(expected_presence, room_id, user_id)

        online = self.matrix.is_online(room_id, user_id)

        self.assertFalse(online)

    def _mock_get_presence(self, expected_presence, room_id, user_id):
        mocked_room = mock.Mock()
        mocked_user = mock.Mock()
        mocked_user.presence = expected_presence
        mocked_room.users = {user_id: mocked_user}
        rooms = {room_id: mocked_room}
        self.matrix.matrix_client.rooms = rooms


class TestRecentRoomMessages(IsolatedAsyncioTestCase):
    def setUp(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock
        config = Mock()
        config.get.return_value = None
        self.client = SimpleNamespace(room_context=AsyncMock(), room_messages=AsyncMock())
        self.matrix = Matrix(config, self.client)

    @staticmethod
    def event(event_id, sender="@alice:example.org", body="Hello", **content):
        from types import SimpleNamespace
        return SimpleNamespace(event_id=event_id, source={
            "event_id": event_id, "sender": sender, "type": "m.room.message",
            "content": {"msgtype": "m.text", "body": body, **content}})

    def context(self, before=(), after=(), token=None):
        from nio import RoomContextResponse
        return RoomContextResponse("!room", token, "after", self.event("$ask"), list(before), list(after), [])

    async def test_twenty_messages_include_bot_and_ignore_future_events(self):
        events = [self.event("$" + str(n), "@bot:example.org" if n % 2 else "@alice:example.org", str(n))
                  for n in range(25)]
        self.client.room_context.return_value = self.context(reversed(events), [self.event("$future")])
        result = await self.matrix.recent_messages("!room", "$ask")
        self.assertEqual([item["message"] for item in result], [str(n) for n in range(5, 25)])
        self.assertIn("@bot:example.org", {item["sender"] for item in result})
        self.client.room_context.assert_awaited_once_with("!room", "$ask", limit=40)
        self.client.room_messages.assert_not_called()

    async def test_pagination_filters_non_text_edits_redactions_and_duplicates(self):
        from nio import RoomMessagesResponse
        media = self.event("$media", msgtype="m.image")
        edit = self.event("$edit", **{"m.relates_to": {"rel_type": "m.replace"}})
        redacted = self.event("$redacted")
        redacted.source["unsigned"] = {"redacted_because": {"type": "m.room.redaction"}}
        member = self.event("$member")
        member.source["type"] = "m.room.member"
        nearest = self.event("$new", body="New")
        self.client.room_context.return_value = self.context(
            [self.event("$ask"), nearest, media, edit, redacted, member, self.event("$blank", body=" ")],
            [self.event("$future")], "older")
        self.client.room_messages.return_value = RoomMessagesResponse(
            "!room", [nearest, self.event("$old", "@bob:example.org", "Old"), self.event("$ask")], "older", None)
        result = await self.matrix.recent_messages("!room", "$ask")
        self.assertEqual(result, [{"sender": "@bob:example.org", "message": "Old"},
                                  {"sender": "@alice:example.org", "message": "New"}])
        self.client.room_messages.assert_awaited_once_with(
            "!room", start="older", limit=50, message_filter={"types": ["m.room.message"]})

    async def test_empty_history_is_valid(self):
        self.client.room_context.return_value = self.context()
        self.assertEqual(await self.matrix.recent_messages("!room", "$ask"), [])
        self.client.room_messages.assert_not_called()

    async def test_pagination_is_bounded_to_five_requests(self):
        from nio import RoomMessagesResponse
        self.client.room_context.return_value = self.context(token="0")
        self.client.room_messages.side_effect = [
            RoomMessagesResponse("!room", [self.event("$media" + str(n), msgtype="m.image")], str(n), str(n + 1))
            for n in range(4)]
        self.assertEqual(await self.matrix.recent_messages("!room", "$ask"), [])
        self.assertEqual(self.client.room_messages.await_count, 4)

    async def test_repeated_pagination_token_stops(self):
        from nio import RoomMessagesResponse
        self.client.room_context.return_value = self.context(token="same")
        self.client.room_messages.return_value = RoomMessagesResponse("!room", [self.event("$old")], "same", "same")
        self.assertEqual(len(await self.matrix.recent_messages("!room", "$ask")), 1)
        self.client.room_messages.assert_awaited_once()

    async def test_context_errors_and_timeout_are_reported(self):
        import asyncio
        from chaanbot.matrix import RoomHistoryError
        for error in (RuntimeError("unavailable"), asyncio.TimeoutError()):
            self.client.room_context.side_effect = error
            with self.assertRaises(RoomHistoryError):
                await self.matrix.recent_messages("!room", "$ask")

    async def test_total_history_timeout_is_enforced(self):
        import asyncio
        from unittest.mock import patch
        from chaanbot.matrix import RoomHistoryError
        original_timeout = asyncio.timeout
        async def wait(*args, **kwargs):
            await asyncio.Event().wait()
        self.client.room_context.side_effect = wait
        with patch("chaanbot.matrix.asyncio.timeout", side_effect=lambda seconds: original_timeout(0.01)) as timeout:
            with self.assertRaises(RoomHistoryError):
                await self.matrix.recent_messages("!room", "$ask")
            timeout.assert_called_once_with(10)

    async def test_wrong_room_or_anchor_is_rejected(self):
        from chaanbot.matrix import RoomHistoryError
        for field, value in (("room_id", "!other-room"), ("event", self.event("$other-event"))):
            response = self.context([self.event("$old")])
            setattr(response, field, value)
            self.client.room_context.return_value = response
            with self.assertRaises(RoomHistoryError):
                await self.matrix.recent_messages("!room", "$ask")

    async def test_pagination_error_does_not_return_partial_context(self):
        from chaanbot.matrix import RoomHistoryError
        self.client.room_context.return_value = self.context([self.event("$old")], token="older")
        self.client.room_messages.return_value = None
        with self.assertRaises(RoomHistoryError):
            await self.matrix.recent_messages("!room", "$ask")

    async def test_cancellation_propagates(self):
        import asyncio
        self.client.room_context.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.matrix.recent_messages("!room", "$ask")
