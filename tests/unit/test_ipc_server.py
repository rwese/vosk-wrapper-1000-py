"""
Unit tests for IPC server functionality.
"""

import tempfile
import unittest

from vosk_wrapper_1000.ipc_server import IPCServer


class TestIPCServer(unittest.TestCase):
    """Test IPC server functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.socket_path = f"{self.temp_dir}/test.sock"

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_ipc_server_import(self):
        """Test that IPCServer can be imported and instantiated."""
        # This test ensures the import issue is fixed
        server = IPCServer(self.socket_path)
        self.assertIsInstance(server, IPCServer)
        self.assertEqual(server.socket_path, self.socket_path)
        self.assertTrue(server.send_partials)  # default value

    def test_ipc_server_custom_settings(self):
        """Test IPCServer with custom settings."""
        server = IPCServer(self.socket_path, send_partials=False)
        self.assertEqual(server.socket_path, self.socket_path)
        self.assertFalse(server.send_partials)

    def test_ipc_server_attributes(self):
        """Test IPCServer has expected attributes."""
        server = IPCServer(self.socket_path)
        self.assertIsNone(server.server_sock)
        self.assertEqual(len(server.clients), 0)
        self.assertIsInstance(server.session_id, str)
        self.assertIsInstance(server.started_at, float)


if __name__ == "__main__":
    unittest.main()
