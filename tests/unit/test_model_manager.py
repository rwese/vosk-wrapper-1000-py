"""Unit tests for ModelManager."""

import os
import tempfile
import unittest
from unittest.mock import patch

from vosk_core.model_manager import ModelManager


class TestModelManager(unittest.TestCase):
    """Test cases for ModelManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.model_manager = ModelManager()

    def test_model_manager_initialization(self):
        """Test ModelManager initialization."""
        self.assertIsNotNone(self.model_manager.models_dir)
        self.assertIsNotNone(self.model_manager.default_model)

    @patch("vosk_core.model_manager.get_models_dir")
    def test_list_available_models_empty(self, mock_get_models_dir):
        """Test listing models when none exist."""
        mock_get_models_dir.return_value = "/nonexistent/path"

        manager = ModelManager()
        models = manager.list_available_models()

        self.assertEqual(models, [])

    @patch("vosk_core.model_manager.get_models_dir")
    def test_list_available_models_with_models(self, mock_get_models_dir):
        """Test listing models when some exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_get_models_dir.return_value = temp_dir

            # Create some model directories
            os.makedirs(os.path.join(temp_dir, "model1"))
            os.makedirs(os.path.join(temp_dir, "model2"))
            # Create a file (should not be listed)
            open(os.path.join(temp_dir, "not_a_model.txt"), "w").close()

            manager = ModelManager()
            models = manager.list_available_models()

            self.assertEqual(len(models), 2)
            self.assertIn("model1", models)
            self.assertIn("model2", models)
            self.assertNotIn("not_a_model.txt", models)

    def test_get_model_sample_rate_from_config(self):
        """Test extracting sample rate from mfcc.conf."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create conf directory and mfcc.conf file
            conf_dir = os.path.join(temp_dir, "conf")
            os.makedirs(conf_dir)

            mfcc_conf = os.path.join(conf_dir, "mfcc.conf")
            with open(mfcc_conf, "w") as f:
                f.write("--sample-frequency=16000\n")
                f.write("--num-ceps=13\n")

            rate = self.model_manager.get_model_sample_rate(temp_dir)
            self.assertEqual(rate, 16000)

    def test_get_model_sample_rate_default(self):
        """Test default sample rate when config is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # No conf/mfcc.conf file
            rate = self.model_manager.get_model_sample_rate(temp_dir)
            self.assertEqual(rate, 16000)

    def test_get_model_sample_rate_invalid_config(self):
        """Test sample rate extraction with invalid config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create conf directory and invalid mfcc.conf file
            conf_dir = os.path.join(temp_dir, "conf")
            os.makedirs(conf_dir)

            mfcc_conf = os.path.join(conf_dir, "mfcc.conf")
            with open(mfcc_conf, "w") as f:
                f.write("--sample-frequency=invalid\n")

            rate = self.model_manager.get_model_sample_rate(temp_dir)
            self.assertEqual(rate, 16000)  # Should fall back to default

    def test_validate_model_nonexistent(self):
        """Test validation of non-existent model."""
        is_valid, message = self.model_manager.validate_model("/nonexistent/path")

        self.assertFalse(is_valid)
        self.assertIn("does not exist", message)

    def test_validate_model_not_directory(self):
        """Test validation of path that is not a directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            is_valid, message = self.model_manager.validate_model(temp_file.name)

            self.assertFalse(is_valid)
            self.assertIn("not a directory", message)

    def test_validate_model_missing_files(self):
        """Test validation of model missing required files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Empty directory - missing all required files
            is_valid, message = self.model_manager.validate_model(temp_dir)

            self.assertFalse(is_valid)
            self.assertIn("missing required files", message)
            self.assertIn("am/final.mdl", message)
            self.assertIn("conf/mfcc.conf", message)
            self.assertIn("graph/HCLG.fst", message)

    def test_validate_model_valid(self):
        """Test validation of a valid model structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create required directory structure and files
            os.makedirs(os.path.join(temp_dir, "am"))
            os.makedirs(os.path.join(temp_dir, "conf"))
            os.makedirs(os.path.join(temp_dir, "graph"))

            # Create required files
            open(os.path.join(temp_dir, "am", "final.mdl"), "w").close()
            open(os.path.join(temp_dir, "conf", "mfcc.conf"), "w").close()
            open(os.path.join(temp_dir, "graph", "HCLG.fst"), "w").close()

            is_valid, message = self.model_manager.validate_model(temp_dir)

            self.assertTrue(is_valid)
            self.assertEqual(message, "Model validation passed")

    @patch("vosk_core.model_manager.get_models_dir")
    def test_get_model_info_nonexistent(self, mock_get_models_dir):
        """Test getting info for non-existent model."""
        mock_get_models_dir.return_value = "/nonexistent/path"

        manager = ModelManager()
        info = manager.get_model_info("nonexistent_model")

        self.assertEqual(info["name"], "nonexistent_model")
        self.assertFalse(info["exists"])
        self.assertIsNone(info["sample_rate"])
        self.assertIsNone(info["size_mb"])

    @patch("vosk_core.model_manager.get_models_dir")
    def test_get_model_info_exists(self, mock_get_models_dir):
        """Test getting info for existing model."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_get_models_dir.return_value = temp_dir

            # Create model directory and structure
            model_dir = os.path.join(temp_dir, "test_model")
            os.makedirs(os.path.join(model_dir, "conf"))

            # Create mfcc.conf with sample rate
            mfcc_conf = os.path.join(model_dir, "conf", "mfcc.conf")
            with open(mfcc_conf, "w") as f:
                f.write("--sample-frequency=22050\n")

            # Create some test files to calculate size
            test_file = os.path.join(model_dir, "test_file.txt")
            with open(test_file, "w") as f:
                f.write("x" * (1024 * 1024))  # 1MB file

            manager = ModelManager()
            info = manager.get_model_info("test_model")

            self.assertEqual(info["name"], "test_model")
            self.assertTrue(info["exists"])
            self.assertEqual(info["sample_rate"], 22050)
            self.assertIsNotNone(info["size_mb"])
            self.assertGreater(info["size_mb"], 0)


if __name__ == "__main__":
    unittest.main()
