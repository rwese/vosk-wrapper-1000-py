"""
Unit tests for XDG paths management.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from vosk_simple.xdg_paths import XDGPaths


class TestXDGPaths(unittest.TestCase):
    """Test XDG paths functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch.dict(
        os.environ,
        {
            "XDG_DATA_HOME": "",
            "XDG_CONFIG_HOME": "",
            "XDG_CACHE_HOME": "",
            "HOME": "/tmp/test_home",
        },
    )
    def test_default_paths(self):
        """Test default XDG paths when environment variables are not set."""
        xdg = XDGPaths()

        # Should use HOME/.local/share, etc.
        expected_data = Path("/tmp/test_home/.local/share")
        expected_config = Path("/tmp/test_home/.config")
        expected_cache = Path("/tmp/test_home/.cache")

        self.assertEqual(xdg.get_data_dir(), expected_data)
        self.assertEqual(xdg.get_config_dir(), expected_config)
        self.assertEqual(xdg.get_cache_dir(), expected_cache)

    @patch.dict(
        os.environ,
        {
            "XDG_DATA_HOME": "/custom/data",
            "XDG_CONFIG_HOME": "/custom/config",
            "XDG_CACHE_HOME": "/custom/cache",
        },
    )
    def test_environment_override_paths(self):
        """Test XDG paths when environment variables are set."""
        xdg = XDGPaths()

        self.assertEqual(xdg.get_data_dir(), Path("/custom/data"))
        self.assertEqual(xdg.get_config_dir(), Path("/custom/config"))
        self.assertEqual(xdg.get_cache_dir(), Path("/custom/cache"))

    def test_vosk_specific_paths(self):
        """Test Vosk-specific paths."""
        with patch.dict(os.environ, {"HOME": self.temp_dir}):
            xdg = XDGPaths()

            # Test model path
            model_path = xdg.get_model_dir()
            expected_model = (
                Path(self.temp_dir) / ".local/share/vosk-wrapper-1000/models"
            )
            self.assertEqual(model_path, expected_model)

            # Test config path
            config_path = xdg.get_config_dir("vosk-simple")
            expected_config = Path(self.temp_dir) / ".config/vosk-simple"
            self.assertEqual(config_path, expected_config)

            # Test cache path
            cache_path = xdg.get_cache_dir("vosk-wrapper-1000/pids")
            expected_cache = Path(self.temp_dir) / ".cache/vosk-wrapper-1000/pids"
            self.assertEqual(cache_path, expected_cache)

    def test_ensure_directory_creation(self):
        """Test directory creation functionality."""
        with patch.dict(os.environ, {"HOME": self.temp_dir}):
            xdg = XDGPaths()

            # Get a path that doesn't exist
            test_path = xdg.get_data_dir("vosk-simple/test")

            # Directory should be created
            self.assertTrue(test_path.exists())
            self.assertTrue(test_path.is_dir())

    def test_path_with_subdirectory(self):
        """Test path generation with subdirectories."""
        with patch.dict(os.environ, {"HOME": self.temp_dir}):
            xdg = XDGPaths()

            # Test with subdirectory
            path = xdg.get_data_dir("vosk-wrapper-1000/models")
            expected = Path(self.temp_dir) / ".local/share/vosk-wrapper-1000/models"
            self.assertEqual(path, expected)

            # Directory should be created
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
