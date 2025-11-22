"""
Unit tests for XDG paths management.
"""

import os
import tempfile
import unittest
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

    def test_xdg_paths_creation(self):
        """Test XDGPaths object creation."""
        xdg = XDGPaths()
        self.assertEqual(xdg.app_name, "vosk-wrapper-1000")

        custom_xdg = XDGPaths("custom-app")
        self.assertEqual(custom_xdg.app_name, "custom-app")

    def test_directory_creation(self):
        """Test directory creation functionality."""
        with patch.dict(os.environ, {"HOME": self.temp_dir}):
            xdg = XDGPaths()

            # Get paths - they should be created
            data_dir = xdg.get_data_dir()
            config_dir = xdg.get_config_dir()
            cache_dir = xdg.get_cache_dir()

            # All should exist and be directories
            self.assertTrue(data_dir.exists())
            self.assertTrue(data_dir.is_dir())
            self.assertTrue(config_dir.exists())
            self.assertTrue(config_dir.is_dir())
            self.assertTrue(cache_dir.exists())
            self.assertTrue(cache_dir.is_dir())

            # Should contain app name
            self.assertIn("vosk-wrapper-1000", str(data_dir))
            self.assertIn("vosk-wrapper-1000", str(config_dir))
            self.assertIn("vosk-wrapper-1000", str(cache_dir))

    def test_custom_app_name_paths(self):
        """Test XDGPaths with custom app name."""
        with patch.dict(os.environ, {"HOME": self.temp_dir}):
            xdg = XDGPaths("custom-app")

            data_dir = xdg.get_data_dir()
            expected = Path(self.temp_dir) / ".local/share/custom-app"
            self.assertEqual(data_dir, expected)
            self.assertTrue(data_dir.exists())

    def test_environment_variables(self):
        """Test that environment variables are respected."""
        custom_data = Path(self.temp_dir) / "custom_data"
        custom_config = Path(self.temp_dir) / "custom_config"
        custom_cache = Path(self.temp_dir) / "custom_cache"

        # Create parent directories first
        custom_data.mkdir(parents=True, exist_ok=True)
        custom_config.mkdir(parents=True, exist_ok=True)
        custom_cache.mkdir(parents=True, exist_ok=True)

        with patch.dict(
            os.environ,
            {
                "XDG_DATA_HOME": str(custom_data),
                "XDG_CONFIG_HOME": str(custom_config),
                "XDG_CACHE_HOME": str(custom_cache),
                "HOME": self.temp_dir,
            },
        ):
            xdg = XDGPaths()

            data_dir = xdg.get_data_dir()
            config_dir = xdg.get_config_dir()
            cache_dir = xdg.get_cache_dir()

            # Should use custom directories
            self.assertEqual(data_dir, custom_data / "vosk-wrapper-1000")
            self.assertEqual(config_dir, custom_config / "vosk-wrapper-1000")
            self.assertEqual(cache_dir, custom_cache / "vosk-wrapper-1000")


if __name__ == "__main__":
    unittest.main()
