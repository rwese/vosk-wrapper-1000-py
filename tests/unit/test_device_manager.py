"""
Unit tests for DeviceManager.
"""

import unittest
from unittest.mock import MagicMock, patch

from vosk_simple.device_manager import DeviceManager


class TestDeviceManager(unittest.TestCase):
    """Test DeviceManager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.device_manager = DeviceManager()

    def test_device_manager_initialization(self):
        """Test DeviceManager initialization."""
        manager = DeviceManager()
        self.assertIsNotNone(manager)
        self.assertIsNone(manager.devices_cache)

    @patch("vosk_simple.device_manager.sd.query_devices")
    def test_refresh_devices(self, mock_query):
        """Test device refreshing."""
        # Mock device list
        mock_devices = [
            {
                "name": "Test Device 1",
                "max_input_channels": 2,
                "max_output_channels": 0,
                "default_samplerate": 44100,
            },
            {
                "name": "Test Device 2",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 48000,
            },
        ]
        mock_query.return_value = mock_devices

        manager = DeviceManager()
        devices = manager.refresh_devices()

        # Should return device list
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]["name"], "Test Device 1")
        self.assertEqual(devices[1]["name"], "Test Device 2")

    @patch("vosk_simple.device_manager.sd.query_devices")
    def test_refresh_devices_empty(self, mock_query):
        """Test device refreshing with no devices."""
        mock_query.return_value = []

        manager = DeviceManager()
        devices = manager.refresh_devices()

        # Should return empty list
        self.assertEqual(len(devices), 0)

    def test_get_device_info(self):
        """Test getting device info."""
        with patch("vosk_simple.device_manager.sd.query_devices") as mock_query:
            mock_devices = [
                {
                    "name": "Test Device",
                    "max_input_channels": 2,
                    "max_output_channels": 0,
                    "default_samplerate": 44100,
                }
            ]
            mock_query.return_value = mock_devices

            manager = DeviceManager()
            device = manager.get_device_info("Test Device")

            # Should find the device
            self.assertIsNotNone(device)
            self.assertEqual(device["name"], "Test Device")

    def test_get_device_info_by_id(self):
        """Test getting device info by ID."""
        with patch("vosk_simple.device_manager.sd.query_devices") as mock_query:
            mock_devices = [
                {
                    "name": "Test Device",
                    "max_input_channels": 2,
                    "max_output_channels": 0,
                    "default_samplerate": 44100,
                }
            ]
            mock_query.return_value = mock_devices

            manager = DeviceManager()
            device = manager.get_device_info("0")

            # Should find the device (ID 0)
            self.assertIsNotNone(device)
            self.assertEqual(device["name"], "Test Device")

    def test_get_device_info_not_found(self):
        """Test getting device info when not found."""
        with patch("vosk_simple.device_manager.sd.query_devices") as mock_query:
            mock_devices = [
                {
                    "name": "Other Device",
                    "max_input_channels": 2,
                    "max_output_channels": 0,
                    "default_samplerate": 44100,
                }
            ]
            mock_query.return_value = mock_devices

            manager = DeviceManager()
            device = manager.get_device_info("Nonexistent Device")

            # Should return None
            self.assertIsNone(device)

    def test_validate_device_for_model(self):
        """Test device validation for model."""
        with patch("sounddevice.query_devices") as mock_query, patch(
            "sounddevice.RawInputStream"
        ) as mock_stream:
            # Mock device info for specific device ID
            mock_device_info = {
                "name": "Compatible Device",
                "max_input_channels": 2,
                "max_output_channels": 0,
                "default_samplerate": 16000,
            }
            mock_query.return_value = mock_device_info

            # Mock successful stream creation
            mock_stream_instance = MagicMock()
            mock_stream.return_value = mock_stream_instance

            manager = DeviceManager()
            is_valid, message = manager.validate_device_for_model(0, 16000)

            # Should be valid
            self.assertTrue(is_valid)
            self.assertIn("supports", message.lower())

    def test_validate_device_for_model_incompatible(self):
        """Test device validation for incompatible model."""
        with patch("sounddevice.query_devices") as mock_query, patch(
            "sounddevice.RawInputStream"
        ) as mock_stream:
            # Mock device info for specific device ID
            mock_device_info = {
                "name": "Incompatible Device",
                "max_input_channels": 2,
                "max_output_channels": 0,
                "default_samplerate": 48000,
            }
            mock_query.return_value = mock_device_info

            # Mock failed stream creation
            mock_stream.side_effect = Exception("Stream creation failed")

            manager = DeviceManager()
            is_valid, message = manager.validate_device_for_model(0, 16000)

            # Should not be valid
            self.assertFalse(is_valid)
            self.assertIn("failed", message.lower())


if __name__ == "__main__":
    unittest.main()
