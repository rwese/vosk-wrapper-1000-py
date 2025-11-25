"""
Integration tests for CLI command functions.
"""

import argparse
import tempfile
import unittest
from unittest.mock import patch

from vosk_wrapper_1000.main import cmd_list, cmd_start, cmd_stop, cmd_terminate


class TestCLICommands(unittest.TestCase):
    """Test CLI command functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("vosk_wrapper_1000.main.send_signal_to_instance")
    def test_cmd_start_success(self, mock_send_signal):
        """Test cmd_start with successful signal send."""
        mock_send_signal.return_value = True

        # Create mock args
        args = argparse.Namespace()
        args.name = "test-instance"

        # Mock sys.exit to prevent test from exiting
        with patch("sys.exit") as mock_exit:
            cmd_start(args)

        # Verify signal was sent
        mock_send_signal.assert_called_once_with("test-instance", 10)  # SIGUSR1

    @patch("vosk_wrapper_1000.main.send_signal_to_instance")
    def test_cmd_start_failure(self, mock_send_signal):
        """Test cmd_start with failed signal send."""
        mock_send_signal.return_value = False

        # Create mock args
        args = argparse.Namespace()
        args.name = "test-instance"

        # Should exit with code 1 on failure
        with patch("sys.exit") as mock_exit:
            cmd_start(args)

        mock_exit.assert_called_once_with(1)

    @patch("vosk_wrapper_1000.main.send_signal_to_instance")
    def test_cmd_stop_success(self, mock_send_signal):
        """Test cmd_stop with successful signal send."""
        mock_send_signal.return_value = True

        # Create mock args
        args = argparse.Namespace()
        args.name = "test-instance"

        # Mock sys.exit to prevent test from exiting
        with patch("sys.exit") as mock_exit:
            cmd_stop(args)

        # Verify signal was sent
        mock_send_signal.assert_called_once_with("test-instance", 12)  # SIGUSR2

    @patch("vosk_wrapper_1000.main.send_signal_to_instance")
    def test_cmd_stop_failure(self, mock_send_signal):
        """Test cmd_stop with failed signal send."""
        mock_send_signal.return_value = False

        # Create mock args
        args = argparse.Namespace()
        args.name = "test-instance"

        # Should exit with code 1 on failure
        with patch("sys.exit") as mock_exit:
            cmd_stop(args)

        mock_exit.assert_called_once_with(1)

    @patch("vosk_wrapper_1000.main.send_signal_to_instance")
    def test_cmd_terminate_success(self, mock_send_signal):
        """Test cmd_terminate with successful signal send."""
        mock_send_signal.return_value = True

        # Create mock args
        args = argparse.Namespace()
        args.name = "test-instance"

        # Mock sys.exit to prevent test from exiting
        with patch("sys.exit") as mock_exit:
            cmd_terminate(args)

        # Verify signal was sent
        mock_send_signal.assert_called_once_with("test-instance", 15)  # SIGTERM

    @patch("vosk_wrapper_1000.main.send_signal_to_instance")
    def test_cmd_terminate_failure(self, mock_send_signal):
        """Test cmd_terminate with failed signal send."""
        mock_send_signal.return_value = False

        # Create mock args
        args = argparse.Namespace()
        args.name = "test-instance"

        # Should exit with code 1 on failure
        with patch("sys.exit") as mock_exit:
            cmd_terminate(args)

        mock_exit.assert_called_once_with(1)

    @patch("builtins.print")
    @patch("vosk_wrapper_1000.pid_manager.list_instances")
    def test_cmd_list(self, mock_list_instances, mock_print):
        """Test cmd_list displays instances correctly."""
        # Mock instances data
        mock_list_instances.return_value = [
            ("default", 12345),
            ("test-instance", 12346),
        ]

        # Create mock args
        args = argparse.Namespace()

        cmd_list(args)

        # Verify list_instances was called
        mock_list_instances.assert_called_once()

        # Verify output format (should print header and instances)
        expected_calls = [
            unittest.mock.call("Name                 PID       "),
            unittest.mock.call("------------------------------"),
            unittest.mock.call("default              12345     "),
            unittest.mock.call("test-instance        12346     "),
        ]
        mock_print.assert_has_calls(expected_calls)

    @patch("builtins.print")
    @patch("vosk_wrapper_1000.pid_manager.list_instances")
    def test_cmd_list_no_instances(self, mock_list_instances, mock_print):
        """Test cmd_list when no instances are running."""
        # Mock empty instances list
        mock_list_instances.return_value = []

        # Create mock args
        args = argparse.Namespace()

        cmd_list(args)

        # Verify list_instances was called
        mock_list_instances.assert_called_once()

        # Should print "No running instances found"
        mock_print.assert_called_once_with("No running instances found")


if __name__ == "__main__":
    unittest.main()
