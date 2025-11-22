"""Audio recording utilities for vosk-wrapper-1000."""

import sys
import wave
from typing import Optional

import numpy as np


class AudioRecorder:
    """Handles WAV audio recording with proper cleanup."""

    def __init__(self, filename: str, sample_rate: int):
        self.filename = filename
        self.sample_rate = sample_rate
        self.file: Optional[wave.Wave_write] = None
        self.is_recording = False

    def start_recording(self) -> bool:
        """Start recording to WAV file."""
        try:
            self.file = wave.open(self.filename, "wb")
            self.file.setnchannels(1)  # Mono
            self.file.setsampwidth(2)  # 16-bit
            self.file.setframerate(self.sample_rate)
            self.is_recording = True
            return True
        except Exception as e:
            print(f"Error starting recording: {e}", file=sys.stderr)
            return False

    def write_audio(self, audio_data: np.ndarray):
        """Write audio data to recording file."""
        if self.is_recording and self.file:
            self.file.writeframes(audio_data.tobytes())

    def stop_recording(self):
        """Stop recording and close file."""
        if self.file:
            self.file.close()
            self.is_recording = False
            self.file = None

    def cleanup(self):
        """Clean up recording resources."""
        if self.is_recording and self.file:
            self.stop_recording()
