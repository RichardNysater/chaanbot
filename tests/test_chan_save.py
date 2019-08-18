from unittest import TestCase
from unittest.mock import Mock, patch, mock_open

from chaanbot.modules.chan_save import ChanSave


class TestChanSave(TestCase):
    url_to_access_saved_files = "https://location/i/"
    save_dirpath = "/dir/to/save"
    event = {"sender": "user_id"}

    @patch('os.access')
    def setUp(self, mock_os_access) -> None:
        mock_os_access.return_value = True
        config = Mock()
        config.get.side_effect = self.get_config_side_effect
        self.requests = Mock()
        self.room = Mock()
        self.chan_save = ChanSave(config, Mock(), Mock(), self.requests)

    @patch('os.access')
    def test_disabled_if_no_save_dirpath(self, mock_os_access):
        mock_os_access.return_value = True
        config = Mock()
        config.get.side_effect = self.get_config_side_effect_without_save_dirpath
        chan_save = ChanSave(config, Mock(), Mock(), self.requests)
        self.assertTrue(chan_save.disabled)

    @patch('os.access')
    def test_enabled_if_no_url_to_access_saved_files(self, mock_os_access):
        mock_os_access.return_value = True
        config = Mock()
        config.get.side_effect = self.get_config_side_effect_without_url_to_access_saved_files
        chan_save = ChanSave(config, Mock(), Mock(), self.requests)
        self.assertFalse(hasattr(chan_save, "disabled"))

    @patch('os.access')
    def test_disabled_if_no_write_access(self, mock_os_access):
        mock_os_access.return_value = False
        config = Mock()
        config.get.side_effect = self.get_config_side_effect
        chan_save = ChanSave(config, Mock(), Mock(), self.requests)
        self.assertTrue(chan_save.disabled)

    def test_config_has_properties(self):
        self.assertTrue(self.chan_save.always_run)
        self.assertIsNotNone(self.chan_save.url_to_access_saved_files)
        self.assertIsNotNone(self.chan_save.save_dirpath)
        self.assertFalse(hasattr(self.chan_save, "disabled"))

    @patch("uuid.uuid1")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_4chan_media_and_send_URL(self, mock_open, mock_uuid):
        uuid = "123123"
        mock_uuid.return_value = uuid
        self.chan_save.run(self.room, self.event, "https://4chan.org/g/stallman.jpg")

        expected_message = "File saved to {}{}{}.".format(self.chan_save.url_to_access_saved_files, uuid, ".jpg")
        self.room.send_text.assert_called_with(expected_message)
        self.requests.get.assert_called_once()
        mock_open().write.assert_called_once()

    @patch("uuid.uuid1")
    @patch("builtins.open", new_callable=mock_open)
    @patch('os.access')
    def test_save_4chan_media_and_dont_send_URL(self, mock_os_access, mock_open, mock_uuid):
        mock_os_access.return_value = True
        config = Mock()
        config.get.side_effect = self.get_config_side_effect_without_url_to_access_saved_files
        chan_save = ChanSave(config, Mock(), Mock(), self.requests)

        uuid = "123123"
        mock_uuid.return_value = uuid
        chan_save.run(self.room, self.event, "https://4chan.org/g/stallman.jpg")

        self.requests.get.assert_called_once()
        mock_open().write.assert_called_once()
        self.room.send_text.assert_not_called()

    def test_dont_save_media_if_unsupported_file_extension(self):
        self.chan_save.run(self.room, self.event, "https://4chan.org/g/stallman.what")

        self.room.send_text.assert_not_called()
        self.requests.get.assert_not_called()

    def test_dont_save_media_and_send_location_if_not_support_4chan_link(self):
        self.chan_save.run(self.room, self.event, "https://4chun.org/g/stallman.jpg")

        self.room.send_text.assert_not_called()
        self.requests.get.assert_not_called()

    def get_config_side_effect(*args, **kwargs):
        if args[1] == "chan_save":
            if args[2] == "url_to_access_saved_files":
                return "url_to_access_saved_files"
            elif args[2] == "save_dirpath":
                return "save_dirpath"
        return None

    def get_config_side_effect_without_save_dirpath(*args, **kwargs):
        if args[1] == "chan_save":
            if args[2] == "url_to_access_saved_files":
                return "url_to_access_saved_files"
        return None

    def get_config_side_effect_without_url_to_access_saved_files(*args, **kwargs):
        if args[1] == "chan_save":
            if args[2] == "save_dirpath":
                return "save_dirpath"
        return None
