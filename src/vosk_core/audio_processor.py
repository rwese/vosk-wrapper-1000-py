"""Audio processing utilities for vosk-wrapper-1000."""

from collections import deque
from typing import Deque, List, Optional

import noisereduce as nr
import numpy as np
import soxr


class AudioProcessor:
    """Handles mono audio processing including noise filtering and resampling."""

    def __init__(
        self,
        device_rate: int,
        model_rate: int,
        noise_filter_enabled: bool = True,
        noise_reduction_strength: float = 0.05,
        stationary_noise: bool = False,
        silence_threshold: float = 50.0,
        normalize_audio: bool = False,
        normalization_target_level: float = 0.3,
        pre_roll_duration: float = 0.5,
        vad_hysteresis_chunks: int = 10,
        noise_reduction_min_rms_ratio: float = 0.5,
    ):
        self.device_rate = device_rate
        self.model_rate = model_rate
        self.noise_filter_enabled = noise_filter_enabled
        self.noise_reduction_strength = noise_reduction_strength
        self.stationary_noise = stationary_noise
        self.silence_threshold = silence_threshold
        self.normalize_audio = normalize_audio
        self.normalization_target_level = normalization_target_level
        self.pre_roll_duration = pre_roll_duration
        self.vad_hysteresis_chunks = vad_hysteresis_chunks
        self.noise_reduction_min_rms_ratio = noise_reduction_min_rms_ratio
        self.soxr_resampler: Optional[soxr.ResampleStream] = None

        # Ring buffer for pre-roll audio (stores processed chunks before speech detection)
        # Buffer size: enough chunks to cover pre_roll_duration at model_rate
        # Estimate: pre_roll_duration * model_rate / avg_chunk_size
        # Using blocksize=1024, after resampling we get roughly (1024 * model_rate / device_rate) samples
        # To be safe, allocate based on number of chunks needed for pre_roll_duration
        self.pre_roll_buffer: Deque[np.ndarray] = deque(
            maxlen=200
        )  # Max 200 chunks in buffer (increased for longer pre-roll durations)
        self.pre_roll_samples = int(pre_roll_duration * model_rate)

        # Track if we're currently in a speech segment
        self.in_speech = False
        # Track consecutive silent chunks for hysteresis
        self.consecutive_silent_chunks = 0
        # Flag to indicate if speech just ended in the last call
        self.speech_just_ended = False

        # Initialize soxr resampler if needed
        if device_rate != model_rate:
            self.soxr_resampler = soxr.ResampleStream(
                in_rate=device_rate, out_rate=model_rate, num_channels=1, quality="HQ"
            )

    def has_audio(self, audio_data: np.ndarray) -> bool:
        """Check if audio data contains meaningful sound above silence threshold.

        Args:
            audio_data: Audio data as numpy array (mono)

        Returns:
            True if audio contains sound above threshold, False if silent
        """
        if len(audio_data) == 0:
            return False

        # Calculate RMS (Root Mean Square) energy after removing DC offset
        audio_float = audio_data.astype(np.float32)
        # Remove DC offset
        audio_float = audio_float - np.mean(audio_float)
        rms = np.sqrt(np.mean(audio_float**2))

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
        current_rms = np.sqrt(np.mean(audio_float**2))

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
            audio_data: Audio data as int16 numpy array (mono)

        Returns:
            Processed mono audio as int16 numpy array
        """
        # Audio is already mono
        processed_audio = audio_data

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

    def _process_mono_audio_chunk(self, mono_audio: np.ndarray) -> np.ndarray:
        """Process a chunk of mono audio data with noise filtering and resampling.

        This is similar to process_audio_chunk but assumes audio is already mono.

        Args:
            mono_audio: Mono audio data as int16 numpy array

        Returns:
            Processed mono audio as int16 numpy array
        """
        processed_audio = mono_audio

        # Apply normalization if enabled (before noise reduction)
        if self.normalize_audio:
            processed_audio = self.normalize_audio_chunk(processed_audio)

        # Apply noise filtering if enabled
        if self.noise_filter_enabled and len(processed_audio) > 1024:
            # Store original audio for volume comparison
            original_audio = processed_audio.copy()

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
            noise_reduced_audio = np.clip(audio_float * 32768.0, -32768, 32767).astype(
                np.int16
            )

            # Validate that noise reduction didn't remove too much signal
            # Check RMS of both original and processed audio
            original_rms = np.sqrt(
                np.mean(
                    (
                        original_audio.astype(np.float32)
                        - np.mean(original_audio.astype(np.float32))
                    )
                    ** 2
                )
            )
            processed_rms = np.sqrt(
                np.mean(
                    (
                        noise_reduced_audio.astype(np.float32)
                        - np.mean(noise_reduced_audio.astype(np.float32))
                    )
                    ** 2
                )
            )

            # If processed audio has adequate volume after noise reduction, use it
            # This prevents over-aggressive noise reduction from removing speech
            if processed_rms > original_rms * self.noise_reduction_min_rms_ratio:
                processed_audio = noise_reduced_audio
            # Else: keep original audio (noise reduction was too aggressive)

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

    def get_pre_roll_audio(self) -> np.ndarray:
        """Get accumulated pre-roll audio from the ring buffer.

        The pre-roll buffer stores unprocessed mono audio. This method processes
        all buffered chunks and returns them ready for speech recognition.

        Returns:
            Processed and concatenated audio from the ring buffer, limited to pre_roll_samples
        """
        if not self.pre_roll_buffer:
            return np.array([], dtype=np.int16)

        # Process each buffered chunk through the audio pipeline
        # (normalization, noise reduction, resampling)
        processed_chunks = []
        for chunk in self.pre_roll_buffer:
            processed_chunk = self._process_mono_audio_chunk(chunk)
            if len(processed_chunk) > 0:
                processed_chunks.append(processed_chunk)

        if not processed_chunks:
            return np.array([], dtype=np.int16)

        # Concatenate all processed chunks
        buffered_audio = np.concatenate(processed_chunks)

        # Trim to pre_roll_duration (keep only the most recent pre_roll_samples)
        # Note: pre_roll_samples is at model_rate, which matches processed audio rate
        if len(buffered_audio) > self.pre_roll_samples:
            buffered_audio = buffered_audio[-self.pre_roll_samples :]

        return buffered_audio

    def process_with_vad(self, audio_data: np.ndarray) -> List[np.ndarray]:
        """Process audio chunk with Voice Activity Detection and pre-roll buffering.

        This method implements a ring buffer that captures audio before speech begins,
        preventing the cutting off of word beginnings.

        Args:
            audio_data: Raw audio data as int16 numpy array (mono)

        Returns:
            List of audio chunks to send to speech recognition:
            - Empty list if silence detected and not in speech
            - Pre-roll audio + current chunk if speech just started
            - Current chunk if continuing speech
        """
        # Audio is already mono
        mono_audio = audio_data

        # Process the audio (normalization, noise reduction, resampling)
        # IMPORTANT: We must process BEFORE checking has_audio, because:
        # 1. Noise reduction can remove background noise, revealing true speech signal
        # 2. Normalization can amplify quiet speech to detectable levels
        # 3. Checking on raw audio causes false negatives for quiet/distant speech
        processed_audio = self._process_mono_audio_chunk(mono_audio)

        # Check if processed audio contains meaningful sound above threshold
        # Note: Check at model_rate after resampling for accurate RMS calculation
        has_audio = self.has_audio(processed_audio)

        # If silence detected and not currently in speech, skip sending to recognition
        if not has_audio and not self.in_speech:
            # Add original mono audio to ring buffer for potential pre-roll
            # (Store unprocessed to avoid accumulating processing artifacts)
            if len(mono_audio) > 0:
                self.pre_roll_buffer.append(mono_audio.copy())
            # Return empty list (don't send to recognition)
            return []

        result = []

        if has_audio:
            # Audio detected - enter/continue speech mode
            if not self.in_speech:
                # Transition from silence to speech
                # Flush pre-roll buffer to capture audio before speech detection
                pre_roll = self.get_pre_roll_audio()
                if len(pre_roll) > 0:
                    result.append(pre_roll)

                self.in_speech = True
                # Clear buffer since we've used it
                self.pre_roll_buffer.clear()

            # Reset silent chunk counter
            self.consecutive_silent_chunks = 0

            # Add current chunk (whether transitioning or continuing speech)
            result.append(processed_audio)

        else:
            # Silence detected
            self.consecutive_silent_chunks += 1

            if self.in_speech:
                # In speech but current chunk is silent
                if self.consecutive_silent_chunks <= self.vad_hysteresis_chunks:
                    # Allow natural pauses in speech - keep gate open AND send chunk
                    # This allows the recognizer to handle natural pauses in speech
                    result.append(processed_audio)
                else:
                    # Too many consecutive silent chunks - exit speech mode
                    self.in_speech = False
                    self.consecutive_silent_chunks = 0
                    self.speech_just_ended = True
                    # Don't send this chunk, and reset VAD state
                    self.pre_roll_buffer.clear()
            else:
                # Not in speech, silence detected
                # Add to ring buffer for potential pre-roll
                if len(mono_audio) > 0:
                    self.pre_roll_buffer.append(mono_audio.copy())
                # Return empty list (don't send to recognition)

        return result

    def check_and_reset_speech_end(self) -> bool:
        """Check if speech just ended and reset the flag.

        Returns:
            True if speech ended in the last process_with_vad call, False otherwise
        """
        ended = self.speech_just_ended
        self.speech_just_ended = False
        return ended

    def reset_vad_state(self):
        """Reset Voice Activity Detection state.

        Should be called when stopping listening or starting a new session.
        """
        self.in_speech = False
        self.consecutive_silent_chunks = 0
        self.speech_just_ended = False
        self.pre_roll_buffer.clear()

    def cleanup(self):
        """Clean up audio processing resources."""
        self.soxr_resampler = None
        self.pre_roll_buffer.clear()
        self.in_speech = False
        self.consecutive_silent_chunks = 0
        self.speech_just_ended = False
