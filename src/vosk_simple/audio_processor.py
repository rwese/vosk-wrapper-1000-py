"""Audio processing utilities for vosk-wrapper-1000."""

import numpy as np
import noisereduce as nr
import soxr
from typing import Optional


class AudioProcessor:
    """Handles audio processing including noise filtering and resampling."""

    def __init__(
        self,
        device_rate: int,
        model_rate: int,
        noise_filter_enabled: bool = True,
        noise_reduction_strength: float = 0.2,
        stationary_noise: bool = True,
    ):
        self.device_rate = device_rate
        self.model_rate = model_rate
        self.noise_filter_enabled = noise_filter_enabled
        self.noise_reduction_strength = noise_reduction_strength
        self.stationary_noise = stationary_noise
        self.soxr_resampler: Optional[soxr.ResampleStream] = None

        # Initialize soxr resampler if needed
        if device_rate != model_rate:
            self.soxr_resampler = soxr.ResampleStream(
                rate_in=device_rate, rate_out=model_rate, num_channels=1, quality="HQ"
            )

    def process_audio_chunk(self, audio_data: np.ndarray) -> np.ndarray:
        """Process a chunk of audio data with noise filtering and resampling."""
        processed_audio = audio_data.copy()

        # Apply noise filtering if enabled
        if self.noise_filter_enabled:
            # Convert to float for noise reduction
            audio_float = processed_audio.astype(np.float32) / 32768.0
            # Apply configurable noise reduction
            audio_float = nr.reduce_noise(
                y=audio_float,
                sr=self.device_rate,
                stationary=self.stationary_noise,
                prop_decrease=self.noise_reduction_strength,
            )
            # Convert back to int16
            processed_audio = np.clip(audio_float * 32767, -32768, 32767).astype(
                np.int16
            )

        # Resample if needed using soxr
        if self.device_rate != self.model_rate and self.soxr_resampler:
            # Convert to float for soxr
            audio_float = processed_audio.astype(np.float32) / 32768.0
            # Resample using soxr
            resampled_float = self.soxr_resampler.resample_chunk(
                audio_float.reshape(-1, 1), last=False
            )
            # Convert back to int16
            processed_audio = np.clip(resampled_float * 32767, -32768, 32767).astype(
                np.int16
            )

        return processed_audio

    def finalize_resampling(self) -> np.ndarray:
        """Finalize resampling by processing the last chunk."""
        if self.soxr_resampler:
            # Process empty chunk with last=True to flush remaining samples
            final_chunk = self.soxr_resampler.resample_chunk(
                np.array([], dtype=np.float32).reshape(-1, 1), last=True
            )
            return np.clip(final_chunk * 32767, -32768, 32767).astype(np.int16)
        return np.array([], dtype=np.int16)

    def cleanup(self):
        """Clean up audio processing resources."""
        self.soxr_resampler = None
