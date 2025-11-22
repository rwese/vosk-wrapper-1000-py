"""
Unit tests for configuration management.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from vosk_simple.config_manager import (
    AudioConfig,
    ConfigManager,
    ModelConfig,
    load_config,
)


class TestConfigManager(unittest.TestCase):
    """Test configuration manager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.yaml"

        # Create a test config file
        test_config = {
            "audio": {
                "device": "test_device",
                "blocksize": 4000,
                "samplerate": 44100,
            },
            "model": {
                "default_name": "test-model",
                "auto_download": True,
            },
            "recognition": {
                "words": True,
                "grammar": "test grammar",
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(test_config, f)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_load_config_from_file(self):
        """Test loading configuration from file."""
        manager = ConfigManager(self.config_file)
        config = manager.load_config()

        self.assertEqual(config.audio.device, "test_device")
        self.assertEqual(config.audio.blocksize, 4000)
        self.assertEqual(config.audio.samplerate, 44100)
        self.assertEqual(config.model.default_name, "test-model")
        self.assertTrue(config.model.auto_download)
        self.assertTrue(config.recognition.words)
        self.assertEqual(config.recognition.grammar, "test grammar")

    def test_load_config_defaults(self):
        """Test loading configuration with defaults."""
        manager = ConfigManager(None)
        config = manager.load_config()

        # Check default values
        self.assertEqual(config.audio.device, "")
        self.assertEqual(config.audio.blocksize, 8000)
        self.assertIsNone(config.audio.samplerate)
        self.assertEqual(config.model.default_name, "vosk-model-small-en-us-0.15")
        self.assertFalse(config.model.auto_download)
        self.assertFalse(config.recognition.words)
        self.assertIsNone(config.recognition.grammar)

    @patch.dict(
        os.environ,
        {
            "VOSK_AUDIO_DEVICE": "env_device",
            "VOSK_AUDIO_BLOCKSIZE": "6000",
            "VOSK_MODEL_NAME": "env_model",
            "VOSK_WORDS": "true",
            "VOSK_LOG_LEVEL": "DEBUG",
        },
    )
    def test_environment_overrides(self):
        """Test environment variable overrides."""
        manager = ConfigManager(self.config_file)
        config = manager.load_config()

        # Environment should override file
        self.assertEqual(config.audio.device, "env_device")
        self.assertEqual(config.audio.blocksize, 6000)
        self.assertEqual(config.model.default_name, "env_model")
        self.assertTrue(config.recognition.words)
        self.assertEqual(config.logging.level, "DEBUG")

        # File values should remain where not overridden
        self.assertEqual(config.audio.samplerate, 44100)

    def test_save_config(self):
        """Test saving configuration to file."""
        manager = ConfigManager()
        config = manager.load_config()

        # Modify some values
        config.audio.device = "saved_device"
        config.model.default_name = "saved_model"

        # Save to new file
        save_file = Path(self.temp_dir) / "saved_config.yaml"
        manager.save_config(config, save_file)

        # Load and verify
        with open(save_file) as f:
            saved_data = yaml.safe_load(f)

        self.assertEqual(saved_data["audio"]["device"], "saved_device")
        self.assertEqual(saved_data["model"]["default_name"], "saved_model")

    def test_invalid_config_file(self):
        """Test handling of invalid config file."""
        invalid_file = Path(self.temp_dir) / "invalid.yaml"
        with open(invalid_file, "w") as f:
            f.write("invalid: yaml: content: [")

        manager = ConfigManager(invalid_file)
        # Should not raise exception, should use defaults
        config = manager.load_config()
        self.assertEqual(config.audio.device, "")

    def test_config_dataclasses(self):
        """Test configuration dataclass creation."""
        audio_config = AudioConfig(device="test", blocksize=4000)
        self.assertEqual(audio_config.device, "test")
        self.assertEqual(audio_config.blocksize, 4000)
        self.assertTrue(audio_config.noise_reduction)  # default value

        model_config = ModelConfig(default_name="test-model")
        self.assertEqual(model_config.default_name, "test-model")
        self.assertFalse(model_config.auto_download)  # default value

    def test_global_load_config(self):
        """Test global load_config function."""
        with patch.dict(os.environ, {"VOSK_AUDIO_DEVICE": "global_test"}):
            config = load_config()
            self.assertEqual(config.audio.device, "global_test")


class TestConfigIntegration(unittest.TestCase):
    """Integration tests for configuration system."""

    def test_full_config_workflow(self):
        """Test complete configuration workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "integration_test.yaml"

            # Create initial config
            manager = ConfigManager()
            config = manager.load_config()

            # Modify and save
            config.audio.device = "integration_device"
            config.recognition.words = True
            manager.save_config(config, config_file)

            # Load with new manager
            new_manager = ConfigManager(config_file)
            loaded_config = new_manager.load_config()

            # Verify persistence
            self.assertEqual(loaded_config.audio.device, "integration_device")
            self.assertTrue(loaded_config.recognition.words)


if __name__ == "__main__":
    unittest.main()
