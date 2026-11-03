from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, patch, AsyncMock

from chaanbot.client import Client


class TestClient(IsolatedAsyncioTestCase):

    async def test_load_environment_on_initialization(self):
        module_runner = AsyncMock()
        matrix = AsyncMock()
        config = Mock()
        config.get.side_effect = self._get_config_side_effect

        client = Client(module_runner, config, matrix)

        config.get.assert_any_call("chaanbot", "allowed_inviters", fallback=None)

        self.assertEqual(["allowed"], client.allowed_inviters)
        self.assertEqual(matrix, client.matrix)
        self.assertEqual(config, client.config)
        pass

    def _get_config_side_effect(*args, **kwargs):
        if args[1] == "chaanbot":
            if args[2] == "modules_path":
                return ""
            elif args[2] == "allowed_inviters":
                return "allowed"
            elif args[2] == "listen_rooms":
                return "listen_room"
        return None

    @patch.object(Client, "_run_forever")
    async def test_join_rooms_and_add_listeners_and_listen_forever_when_ran(self, run_forever_method):
        module_runner = AsyncMock()
        matrix = AsyncMock()
        matrix.matrix_client.rooms = {"room": "room1"}
        matrix.matrix_client.add_event_callback = Mock()
        config = Mock()
        config.get.side_effect = self._get_config_side_effect

        client = Client(module_runner, config, matrix)

        await client.run()
        self.assertEqual(2, matrix.matrix_client.add_event_callback.call_count)
        matrix.join_room.assert_called_once()
        run_forever_method.assert_called_once()

    async def test_shutdown_closes_matrix_even_if_module_cleanup_fails(self):
        module_runner = AsyncMock()
        module_runner.aclose.side_effect = RuntimeError("cleanup failed")
        matrix = AsyncMock()
        matrix.matrix_client.rooms = {}
        config = Mock()
        config.get.return_value = None
        client = Client(module_runner, config, matrix)
        client._join_rooms = AsyncMock()
        client._run_forever = AsyncMock()
        matrix.matrix_client.add_event_callback = Mock()
        with self.assertRaises(RuntimeError):
            await client.run()
        matrix.matrix_client.close.assert_awaited_once()
