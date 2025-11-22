"""
Unit tests for AudioProcessor.
"""

import unittest
from unittest.mock import patch

import numpy as np

from vosk_wrapper_1000.audio_processor import AudioProcessor


class TestAudioProcessor(unittest.TestCase):
    """Test AudioProcessor functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.device_rate = 44100
        self.model_rate = 16000
        self.processor = AudioProcessor(self.device_rate, self.model_rate)

    def test_processor_initialization(self):
        """Test AudioProcessor initialization."""
        processor = AudioProcessor(44100, 16000)
        self.assertEqual(processor.device_rate, 44100)
        self.assertEqual(processor.model_rate, 16000)

    def test_process_audio_chunk_basic(self):
        """Test basic audio chunk processing."""
        # Create a simple sine wave audio chunk
        duration = 0.1  # 100ms
        frequency = 440  # A4 note
        samples = int(duration * self.device_rate)
        t = np.linspace(0, duration, samples, False)
        audio_chunk = np.sin(2 * np.pi * frequency * t).astype(np.float32)

        # Process chunk
        result = self.processor.process_audio_chunk(audio_chunk)

        # Should return processed audio
        self.assertIsInstance(result, np.ndarray)
        # Should be shorter due to resampling from higher to lower rate
        self.assertLess(len(result), len(audio_chunk))

    def test_process_audio_chunk_empty(self):
        """Test processing empty audio chunk."""
        empty_chunk = np.array([], dtype=np.float32)
        result = self.processor.process_audio_chunk(empty_chunk)
        self.assertEqual(len(result), 0)

    def test_process_audio_chunk_none(self):
        """Test processing None audio chunk."""
        with self.assertRaises((TypeError, AttributeError)):
            self.processor.process_audio_chunk(None)

    def test_resample_not_needed(self):
        """Test no resampling when sample rates match."""
        # Create processor with same rate
        processor = AudioProcessor(16000, 16000)

        # Create audio at 16000 Hz
        duration = 0.1
        samples = int(duration * 16000)
        audio_chunk = np.random.normal(0, 0.1, samples).astype(np.float32)

        # Process should not change length
        result = processor.process_audio_chunk(audio_chunk)
        self.assertEqual(len(result), len(audio_chunk))

    @patch("vosk_wrapper_1000.audio_processor.nr.reduce_noise")
    def test_noise_reduction(self, mock_reduce_noise):
        """Test noise reduction is applied."""
        # Mock:: noise reduction function
        mock_reduce_noise.return_value = np.array([1.0, 2.0, 3.0])

        # Create larger audio chunk to trigger noise reduction
        audio_chunk = np.random.normal(0, 0.1, 2000).astype(np.float32)
        self.processor.process_audio_chunk(audio_chunk)

        # Verify noise reduction was called
        mock_reduce_noise.assert_called_once()

    def test_data_type_preservation(self):
        """Test that output data type is preserved."""
        audio_chunk = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        result = self.processor.process_audio_chunk(audio_chunk)
        # AudioProcessor returns int16 after processing
        self.assertEqual(result.dtype, np.int16)


if __name__ == "__main__":
    unittest.main()
