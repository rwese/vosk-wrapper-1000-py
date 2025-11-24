"""Audio processing utilities for vosk-wrapper-1000."""

from typing import Optional

import noisereduce as nr
import numpy as np
import soxr


class AudioProcessor:
    """Handles audio processing including noise filtering and resampling."""

    def __init__(
        self,
        device_rate: int,
        model_rate: int,
        noise_filter_enabled: bool = True,
        noise_reduction_strength: float = 0.05,
        stationary_noise: bool = False,
        silence_threshold: float = 500.0,
        normalize_audio: bool = False,
        normalization_target_level: float = 0.3,
        channels: int = 1,
    ):
        self.device_rate = device_rate
        self.model_rate = model_rate
        self.noise_filter_enabled = noise_filter_enabled
        self.noise_reduction_strength = noise_reduction_strength
        self.stationary_noise = stationary_noise
        self.silence_threshold = silence_threshold
        self.normalize_audio = normalize_audio
        self.normalization_target_level = normalization_target_level
        self.channels = channels
        self.soxr_resampler: Optional[soxr.ResampleStream] = None

        # Initialize soxr resampler if needed
        if device_rate != model_rate:
            self.soxr_resampler = soxr.ResampleStream(
                in_rate=device_rate, out_rate=model_rate, num_channels=1, quality="HQ"
            )

    def convert_to_mono(self, audio_data: np.ndarray) -> np.ndarray:
        """Convert stereo or multi-channel audio to mono.

        Args:
            audio_data: Audio data as int16 numpy array
                       If stereo: shape is (frames * 2,) with interleaved L/R samples
                       If multi-channel: shape is (frames * channels,)

        Returns:
            Mono audio as int16 numpy array with shape (frames,)
        """
        if self.channels == 1:
            # Already mono, return as-is
            return audio_data

        # Reshape interleaved multi-channel data to (frames, channels)
        frames = len(audio_data) // self.channels
        audio_multi = audio_data.reshape(frames, self.channels)

        # Average all channels to create mono (prevents clipping better than just taking left)
        audio_mono = np.mean(audio_multi, axis=1).astype(np.int16)

        return audio_mono

    def has_audio(self, audio_data: np.ndarray) -> bool:
        """Check if audio data contains meaningful sound above silence threshold.

        Args:
            audio_data: Audio data as numpy array (mono)

        Returns:
            True if audio contains sound above threshold, False if silent
        """
        if len(audio_data) == 0:
            return False

        # Calculate RMS (Root Mean Square) energy
        audio_float = audio_data.astype(np.float32)
        rms = np.sqrt(np.mean(audio_float ** 2))

        return rms > self.silence_threshold

    def normalize_audio_chunk(self, audio_data: np.ndarray) -> np.ndarray:
        """Normalize audio to target RMS level.

        Args:
            audio_data: Audio data as int16 numpy array

        Returns:
            Normalized audio as int16 numpy array
        """
        if len(audio_data) == 0:
            return audio_data

        # Convert to float (normalize to [-1.0, 1.0])
        audio_float = audio_data.astype(np.float32) / 32768.0

        # Calculate current RMS
        current_rms = np.sqrt(np.mean(audio_float ** 2))

        # Avoid division by zero or amplifying silence
        if current_rms < 1e-6:
            return audio_data

        # Calculate gain to reach target level
        gain = self.normalization_target_level / current_rms

        # Limit gain to prevent excessive amplification (max 10x)
        gain = min(gain, 10.0)

        # Apply gain
        normalized = audio_float * gain

        # Convert back to int16 with clipping (use 32768.0 for symmetric scaling)
        return np.clip(normalized * 32768.0, -32768, 32767).astype(np.int16)

    def process_audio_chunk(self, audio_data: np.ndarray) -> np.ndarray:
        """Process a chunk of audio data with noise filtering and resampling.

        Args:
            audio_data: Audio data as int16 numpy array (mono or multi-channel)

        Returns:
            Processed mono audio as int16 numpy array
        """
        # Convert to mono if needed (must be first step)
        processed_audio = self.convert_to_mono(audio_data)

        # Apply normalization if enabled (before noise reduction)
        if self.normalize_audio:
            processed_audio = self.normalize_audio_chunk(processed_audio)

        # Apply noise filtering if enabled
        if self.noise_filter_enabled and len(audio_data) > 1024:
            # Convert to float for noise reduction (normalize to [-1.0, 1.0])
            audio_float = processed_audio.astype(np.float32) / 32768.0
            # Apply configurable noise reduction
            audio_float = nr.reduce_noise(
                y=audio_float,
                sr=self.device_rate,
                stationary=self.stationary_noise,
                prop_decrease=self.noise_reduction_strength,
            )
            # Convert back to int16 (use 32768.0 for symmetric scaling)
            processed_audio = np.clip(audio_float * 32768.0, -32768, 32767).astype(
                np.int16
            )

        # Resample if needed using soxr
        if self.device_rate != self.model_rate and self.soxr_resampler:
            # Convert to float for soxr (normalize to [-1.0, 1.0])
            audio_float = processed_audio.astype(np.float32) / 32768.0
            # Resample using soxr
            resampled_float = self.soxr_resampler.resample_chunk(
                audio_float.reshape(-1, 1), last=False
            )
            # Convert back to int16 and flatten to 1D array (use 32768.0 for symmetric scaling)
            processed_audio = (
                np.clip(resampled_float * 32768.0, -32768, 32767)
                .astype(np.int16)
                .flatten()
            )

        return processed_audio

    def finalize_resampling(self) -> np.ndarray:
        """Finalize resampling by processing the last chunk."""
        if self.soxr_resampler:
            # Process empty chunk with last=True to flush remaining samples
            final_chunk = self.soxr_resampler.resample_chunk(
                np.array([], dtype=np.float32).reshape(-1, 1), last=True
            )
            return (
                np.clip(final_chunk * 32768.0, -32768, 32767).astype(np.int16).flatten()
            )
        return np.array([], dtype=np.int16)

    def cleanup(self):
        """Clean up audio processing resources."""
        self.soxr_resampler = None
