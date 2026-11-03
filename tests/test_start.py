from unittest import IsolatedAsyncioTestCase, TestCase


class TestStart(IsolatedAsyncioTestCase):


    """
        @patch("configparser.ConfigParser")
        @patch("os.path.isfile", return_value=True)
        @patch("os.path.exists", return_value=True)
        @patch("appdirs.user_config_dir")
        async def test_read_existing_config_connect_and_start_running_bot_on_start(self, user_config_dir, config_dir_exists,
                                                                                   config_file_exists, config):
            with patch('chaanbot.start.AsyncClient', spec=AsyncClient) as matrix_client:
                with patch('chaanbot.start.Matrix', spec=Matrix) as matrix:
                    with patch('chaanbot.start.Database') as database:
                        with patch('chaanbot.start.ModuleLoader') as module_loader:
                            with patch('chaanbot.start.ModuleRunner') as module_runner:
                                with patch('chaanbot.start.Client') as client:
                                    user_config_dir.return_value = "configdir"
                                    config.return_value.get.side_effect = self._get_config_side_effect

                                    await main()

                                    matrix_client.assert_called_once_with("matrix_server_url", "user_id")
                                    matrix.assert_called_once_with(config.return_value, matrix_client.return_value)
                                    database.assert_called_once_with("sqlite_database_location")
                                    module_loader.assert_called_once_with(config.return_value, database.return_value, ANY)
                                    module_runner.assert_called_once_with(config.return_value, matrix.return_value,
                                                                          module_loader.return_value)
                                    client.assert_called_once_with(module_runner.return_value, config.return_value,
                                                                   matrix.return_value)
                                    client.return_value.run.assert_called_once()

        def _get_config_side_effect(*args, **kwargs):
            if args[1] == "chaanbot":
                if args[2] == "matrix_server_url":
                    return "matrix_server_url"
                elif args[2] == "password":
                    return "apassword"
                elif args[2] == "user_id":
                    return "user_id"
                elif args[2] == "sqlite_database_location":
                    return "sqlite_database_location"
            return None
            """


class TestConsoleEntryPoint(TestCase):
    def test_sigint_cancels_main_and_runs_cleanup(self):
        import asyncio
        from unittest.mock import patch
        from chaanbot import start

        cleaned = []

        async def fake_main():
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.append(True)

        def interrupt():
            raise KeyboardInterrupt

        loop = asyncio.new_event_loop()
        original = loop.run_until_complete
        first = [True]

        def run_until_complete(task):
            if first[0]:
                first[0] = False
                loop.call_soon(interrupt)
            return original(task)

        with patch.object(start, "main", fake_main):
            with patch.object(start.asyncio, "new_event_loop", return_value=loop):
                with patch.object(loop, "run_until_complete", side_effect=run_until_complete):
                    start.run()
        self.assertEqual(cleaned, [True])
        self.assertTrue(loop.is_closed())


class TestSampleConfiguration(TestCase):
    def test_create_user_config_uses_packaged_sample(self):
        import configparser
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from chaanbot.start import create_user_config

        with TemporaryDirectory() as directory:
            destination = Path(directory) / "chaanbot.cfg"
            create_user_config(destination)
            config = configparser.ConfigParser()
            config.read(destination)
        self.assertTrue(config.has_section("chaanbot"))
        self.assertFalse(config.getboolean("ai", "enabled"))
