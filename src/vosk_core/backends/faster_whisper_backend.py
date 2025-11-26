"""FasterWhisper recognition backend implementation."""

import logging

import numpy as np

from ..recognition_backend import RecognitionBackend, RecognitionResult

logger = logging.getLogger(__name__)


class FasterWhisperBackend(RecognitionBackend):
    """FasterWhisper speech recognition backend.

    Note: Whisper models process audio in batches, not streaming.
    Audio is buffered until speech end, then transcribed.
    """

    def __init__(self, model_path: str, sample_rate: int, **options):
        """Initialize FasterWhisper backend.

        Args:
            model_path: Path or name of Whisper model (e.g., 'base.en', 'medium')
            sample_rate: Audio sample rate in Hz (should be 16000 for Whisper)
            **options: FasterWhisper-specific options:
                - device (str): 'cpu', 'cuda', or 'auto'
                - compute_type (str): 'int8', 'int16', 'float16', 'float32'
                - beam_size (int): Beam size for decoding
                - language (str): Language code or None for auto-detect
                - vad_filter (bool): Enable VAD filtering
        """
        from faster_whisper import WhisperModel

        self.model_path = model_path
        self.sample_rate = sample_rate
        self.options = options

        # Get options with defaults
        device = options.get("device", "cpu")
        compute_type = options.get("compute_type", "int8")
        self.beam_size = options.get("beam_size", 5)
        self.language = options.get("language")
        self.vad_filter = options.get("vad_filter", True)

        # Load FasterWhisper model
        logger.info(
            f"Loading FasterWhisper model: {model_path} "
            f"(device={device}, compute_type={compute_type})"
        )
        self.model = WhisperModel(model_path, device=device, compute_type=compute_type)

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
        # Final result will be available when get_final_result() is called
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

            # Transcribe with FasterWhisper
            segments, info = self.model.transcribe(
                audio_float,
                beam_size=self.beam_size,
                language=self.language,
                vad_filter=self.vad_filter,
                word_timestamps=False,  # Can be enabled if needed
            )

            # Collect all segments
            transcription_parts = []
            for segment in segments:
                transcription_parts.append(segment.text)

            text = " ".join(transcription_parts).strip()

            # Calculate average confidence if available
            # FasterWhisper provides confidence per segment
            confidence = 1.0  # Default if not available

            logger.debug(
                f"FasterWhisper transcription: '{text}' "
                f"(detected language: {info.language})"
            )

            return RecognitionResult(
                text=text,
                is_partial=False,
                confidence=confidence,
                words=None,
                alternatives=None,
            )

        except Exception as e:
            logger.error(f"FasterWhisper transcription error: {e}")
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

        Note: FasterWhisper doesn't support grammar constraints.

        Args:
            grammar: Grammar specification (ignored)
        """
        if grammar:
            logger.warning("FasterWhisper backend does not support grammar constraints")

    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "faster-whisper"

    @property
    def supports_partial_results(self) -> bool:
        """Check if backend supports partial results."""
        return False  # Whisper processes in batches

    @property
    def supports_grammar(self) -> bool:
        """Check if backend supports grammar constraints."""
        return False
