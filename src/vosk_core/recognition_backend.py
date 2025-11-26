"""Abstract recognition backend interface for multi-engine support."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class RecognitionResult:
    """Standardized recognition result across all backends."""

    text: str
    is_partial: bool
    confidence: float = 1.0
    words: list[dict[str, Any]] | None = None  # Word-level timestamps if available
    alternatives: list[dict[str, Any]] | None = None  # Alternative transcriptions


class RecognitionBackend(ABC):
    """Abstract base class for speech recognition backends."""

    @abstractmethod
    def __init__(self, model_path: str, sample_rate: int, **options):
        """Initialize the recognition backend.

        Args:
            model_path: Path to the recognition model
            sample_rate: Audio sample rate in Hz
            **options: Backend-specific options
        """
        pass

    @abstractmethod
    def accept_waveform(self, data: bytes) -> bool:
        """Process audio data.

        Args:
            data: Audio data as bytes (int16 PCM format)

        Returns:
            True if final result is ready, False for partial result
        """
        pass

    @abstractmethod
    def get_result(self) -> RecognitionResult:
        """Get final recognition result.

        Returns:
            RecognitionResult with final transcription
        """
        pass

    @abstractmethod
    def get_partial_result(self) -> RecognitionResult:
        """Get partial recognition result (intermediate transcription).

        Returns:
            RecognitionResult with partial transcription
        """
        pass

    @abstractmethod
    def get_final_result(self) -> RecognitionResult:
        """Get final result and flush any pending audio.

        This is called when speech ends or the session terminates
        to ensure all buffered audio is processed.

        Returns:
            RecognitionResult with final transcription
        """
        pass

    @abstractmethod
    def reset(self):
        """Reset recognizer state for next utterance.

        Clears any buffered audio and resets recognition state.
        """
        pass

    @abstractmethod
    def set_grammar(self, grammar: str | None):
        """Set grammar/constraints if supported by backend.

        Args:
            grammar: Grammar specification (format depends on backend)
                    None to disable grammar constraints
        """
        pass

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return backend identifier.

        Returns:
            Backend name (e.g., 'vosk', 'faster-whisper', 'whisper')
        """
        pass

    @property
    @abstractmethod
    def supports_partial_results(self) -> bool:
        """Check if backend supports partial/streaming results.

        Returns:
            True if backend can return partial results during recognition
        """
        pass

    @property
    @abstractmethod
    def supports_grammar(self) -> bool:
        """Check if backend supports grammar constraints.

        Returns:
            True if backend supports grammar/constraints
        """
        pass
