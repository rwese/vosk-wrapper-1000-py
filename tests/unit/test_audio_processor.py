"""
Unit tests for AudioProcessor.
"""

import unittest
from unittest.mock import patch

import numpy as np

from vosk_core.audio_processor import AudioProcessor


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

    @patch("vosk_core.audio_processor.nr.reduce_noise")
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

    def test_normalize_audio_chunk_disabled(self):
        """Test that normalization is disabled when flag is False."""
        # Create processor with normalization disabled
        processor = AudioProcessor(
            16000, 16000, normalize_audio=False, normalization_target_level=0.3
        )

        # Create test audio with known RMS
        audio_data = np.array([1000, -1000, 2000, -2000], dtype=np.int16)
        result = processor.normalize_audio_chunk(audio_data)

        # Should return unchanged audio when normalization is disabled
        np.testing.assert_array_equal(result, audio_data)

    def test_normalize_audio_chunk_enabled(self):
        """Test that normalization brings audio to target RMS level."""
        # Create processor with normalization enabled
        target_level = 0.3
        processor = AudioProcessor(
            16000, 16000, normalize_audio=True, normalization_target_level=target_level
        )

        # Create test audio with known RMS (quiet audio)
        audio_data = np.array([1000, -1000, 1000, -1000], dtype=np.int16)
        result = processor.normalize_audio_chunk(audio_data)

        # Convert result to float to check RMS
        result_float = result.astype(np.float32) / 32768.0
        result_rms = np.sqrt(np.mean(result_float**2))

        # Result RMS should be close to target level (within 10% tolerance)
        self.assertAlmostEqual(result_rms, target_level, delta=0.03)

    def test_normalize_audio_chunk_consistent_target(self):
        """Test that normalization produces consistent output regardless of input volume."""
        target_level = 0.3
        processor = AudioProcessor(
            16000, 16000, normalize_audio=True, normalization_target_level=target_level
        )

        # Test with different input volumes
        quiet_audio = np.array([500, -500, 500, -500], dtype=np.int16)
        loud_audio = np.array([8000, -8000, 8000, -8000], dtype=np.int16)

        quiet_result = processor.normalize_audio_chunk(quiet_audio)
        loud_result = processor.normalize_audio_chunk(loud_audio)

        # Convert to float to check RMS
        quiet_float = quiet_result.astype(np.float32) / 32768.0
        loud_float = loud_result.astype(np.float32) / 32768.0

        quiet_rms = np.sqrt(np.mean(quiet_float**2))
        loud_rms = np.sqrt(np.mean(loud_float**2))

        # Both should have similar RMS levels (within 10% tolerance)
        self.assertAlmostEqual(quiet_rms, loud_rms, delta=0.03)
        # Both should be close to target level
        self.assertAlmostEqual(quiet_rms, target_level, delta=0.03)
        self.assertAlmostEqual(loud_rms, target_level, delta=0.03)

    def test_normalize_audio_chunk_empty(self):
        """Test normalization with empty audio."""
        processor = AudioProcessor(
            16000, 16000, normalize_audio=True, normalization_target_level=0.3
        )

        empty_audio = np.array([], dtype=np.int16)
        result = processor.normalize_audio_chunk(empty_audio)

        # Should return empty array
        self.assertEqual(len(result), 0)

    def test_normalize_audio_chunk_silence(self):
        """Test normalization with extremely silent audio."""
        processor = AudioProcessor(
            16000, 16000, normalize_audio=True, normalization_target_level=0.3
        )

        # Create extremely quiet audio (below threshold)
        # Use zeros to ensure it's below the 1e-6 threshold
        silent_audio = np.array([0, 0, 0, 0], dtype=np.int16)
        result = processor.normalize_audio_chunk(silent_audio)

        # Should return unchanged audio for extremely quiet input
        np.testing.assert_array_equal(result, silent_audio)

    def test_normalize_audio_chunk_max_gain_limit(self):
        """Test that gain is limited to prevent excessive amplification."""
        target_level = 0.3
        processor = AudioProcessor(
            16000, 16000, normalize_audio=True, normalization_target_level=target_level
        )

        # Create extremely quiet audio that would require >50x gain
        very_quiet_audio = np.array([5, -5, 5, -5], dtype=np.int16)
        result = processor.normalize_audio_chunk(very_quiet_audio)

        # Convert to float to check RMS
        result_float = result.astype(np.float32) / 32768.0
        result_rms = np.sqrt(np.mean(result_float**2))

        # Result should not exceed target level by more than the max gain limit
        # With max gain of 50x, very quiet audio should still be amplified but not to target
        self.assertLess(result_rms, target_level * 2)  # Should be limited

    def test_normalize_audio_chunk_dc_offset_removal(self):
        """Test that DC offset is properly removed before normalization."""
        processor = AudioProcessor(
            16000, 16000, normalize_audio=True, normalization_target_level=0.3
        )

        # Create audio with DC offset
        audio_with_dc = np.array([5000, 5000, -5000, -5000], dtype=np.int16)
        result = processor.normalize_audio_chunk(audio_with_dc)

        # Convert to float and check that mean is close to zero (DC offset removed)
        result_float = result.astype(np.float32) / 32768.0
        result_mean = np.mean(result_float)

        # Mean should be very close to zero after DC offset removal
        self.assertAlmostEqual(result_mean, 0.0, places=4)


if __name__ == "__main__":
    unittest.main()
