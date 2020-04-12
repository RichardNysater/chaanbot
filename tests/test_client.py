from unittest import TestCase
from unittest.mock import Mock, patch

from chaanbot.client import Client


class TestClient(TestCase):

    def test_load_environment_on_initialization(self):
        module_runner = Mock()
        matrix = Mock()
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
    def test_join_rooms_and_add_listeners_and_listen_forever_when_ran(self, run_forever_method):
        module_runner = Mock()
        matrix = Mock()
        matrix.matrix_client.rooms = {"room": "room1"}
        config = Mock()
        config.get.side_effect = self._get_config_side_effect

        client = Client(module_runner, config, matrix)

        handler = Mock()
        client.run(handler)
        matrix.matrix_client.add_invite_listener.assert_called_once()
        matrix.matrix_client.add_leave_listener.assert_called_once()
        matrix.matrix_client.start_listener_thread.assert_called_once()
        matrix.join_room.assert_called_once()
        run_forever_method.assert_called_once()
