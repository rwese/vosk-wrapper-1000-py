"""OpenAI Whisper recognition backend implementation."""

import logging

import numpy as np
import torch

from ..recognition_backend import RecognitionBackend, RecognitionResult

logger = logging.getLogger(__name__)


class WhisperBackend(RecognitionBackend):
    """OpenAI Whisper speech recognition backend.

    Note: Whisper models process audio in batches, not streaming.
    Audio is buffered until speech end, then transcribed.
    """

    def __init__(self, model_path: str, sample_rate: int, **options):
        """Initialize Whisper backend.

        Args:
            model_path: Whisper model name (e.g., 'base', 'medium', 'large')
                       or path to model file (.pt)
            sample_rate: Audio sample rate in Hz (should be 16000 for Whisper)
            **options: Whisper-specific options:
                - device (str): 'cpu' or 'cuda'
                - language (str): Language code or None for auto-detect
                - temperature (float): Sampling temperature
                - fp16 (bool): Use FP16 if GPU available
        """
        import whisper

        self.model_path = model_path
        self.sample_rate = sample_rate
        self.options = options

        # Get options with defaults
        device = options.get("device", "cpu")
        self.language = options.get("language")
        self.temperature = options.get("temperature", 0.0)
        self.fp16 = options.get("fp16", False)

        # Auto-detect FP16 support
        if device == "cuda" and not self.fp16:
            self.fp16 = torch.cuda.is_available()

        # Load Whisper model
        logger.info(
            f"Loading Whisper model: {model_path} (device={device}, fp16={self.fp16})"
        )

        # Check if model_path is a model name or file path
        if model_path.endswith(".pt"):
            # Load from file
            self.model = whisper.load_model(model_path, device=device)
        else:
            # Load by name (will download if needed)
            self.model = whisper.load_model(model_path, device=device)

        # Audio buffer for batch processing
        self.audio_buffer: list[np.ndarray] = []
        self._has_speech = False

    def accept_waveform(self, data: bytes) -> bool:
        """Process audio data by buffering it.

        Args:
            data: Audio data as bytes (int16 PCM format)

        Returns:
            False (Whisper processes in batches, not streaming)
        """
        # Convert bytes to numpy array
        audio_array = np.frombuffer(data, dtype=np.int16)

        # Buffer audio for batch processing
        self.audio_buffer.append(audio_array)
        self._has_speech = True

        # Whisper doesn't support streaming, always return False
        return False

    def get_result(self) -> RecognitionResult:
        """Get final recognition result.

        Returns:
            Empty RecognitionResult (use get_final_result for actual transcription)
        """
        # Whisper doesn't provide results until speech ends
        return RecognitionResult(
            text="", is_partial=False, confidence=1.0, words=None, alternatives=None
        )

    def get_partial_result(self) -> RecognitionResult:
        """Get partial recognition result.

        Returns:
            Empty RecognitionResult (Whisper doesn't support partials)
        """
        # Whisper doesn't support partial results
        return RecognitionResult(
            text="", is_partial=True, confidence=1.0, words=None, alternatives=None
        )

    def get_final_result(self) -> RecognitionResult:
        """Get final result by transcribing buffered audio.

        Returns:
            RecognitionResult with transcription
        """
        if not self.audio_buffer:
            return RecognitionResult(
                text="",
                is_partial=False,
                confidence=1.0,
                words=None,
                alternatives=None,
            )

        try:
            # Concatenate all buffered audio
            audio_data = np.concatenate(self.audio_buffer)

            # Convert int16 to float32 normalized to [-1, 1]
            audio_float = audio_data.astype(np.float32) / 32768.0

            # Transcribe with Whisper
            result = self.model.transcribe(
                audio_float,
                language=self.language,
                temperature=self.temperature,
                fp16=self.fp16,
                verbose=False,
            )

            text = result.get("text", "").strip()

            # Whisper doesn't provide confidence scores in the same way
            # Could use log probability if needed
            confidence = 1.0

            detected_language = result.get("language", "unknown")
            logger.debug(
                f"Whisper transcription: '{text}' "
                f"(detected language: {detected_language})"
            )

            return RecognitionResult(
                text=text,
                is_partial=False,
                confidence=confidence,
                words=None,
                alternatives=None,
            )

        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return RecognitionResult(
                text="",
                is_partial=False,
                confidence=0.0,
                words=None,
                alternatives=None,
            )

    def reset(self):
        """Reset recognizer state for next utterance."""
        self.audio_buffer = []
        self._has_speech = False

    def set_grammar(self, grammar: str | None):
        """Set grammar/constraints.

        Note: Whisper doesn't support grammar constraints.

        Args:
            grammar: Grammar specification (ignored)
        """
        if grammar:
            logger.warning("Whisper backend does not support grammar constraints")

    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "whisper"

    @property
    def supports_partial_results(self) -> bool:
        """Check if backend supports partial results."""
        return False  # Whisper processes in batches

    @property
    def supports_grammar(self) -> bool:
        """Check if backend supports grammar constraints."""
        return False
