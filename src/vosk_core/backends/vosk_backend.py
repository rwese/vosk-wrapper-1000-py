"""Vosk recognition backend implementation."""

import json

import vosk

from ..recognition_backend import RecognitionBackend, RecognitionResult


class VoskBackend(RecognitionBackend):
    """Vosk speech recognition backend."""

    def __init__(self, model_path: str, sample_rate: int, **options):
        """Initialize Vosk backend.

        Args:
            model_path: Path to Vosk model directory
            sample_rate: Audio sample rate in Hz
            **options: Vosk-specific options:
                - words (bool): Enable word-level timestamps
                - partial_words (bool): Enable partial word results
                - grammar (str): Grammar specification (JSON array)
                - max_alternatives (int): Number of alternative transcriptions
        """
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.options = options

        # Load Vosk model
        self.model = vosk.Model(str(model_path))

        # Create recognizer with optional grammar
        grammar = options.get("grammar")
        if grammar:
            self.recognizer = vosk.KaldiRecognizer(self.model, sample_rate, grammar)
        else:
            self.recognizer = vosk.KaldiRecognizer(self.model, sample_rate)

        # Configure recognizer options
        if options.get("words", False):
            self.recognizer.SetWords(True)

        if options.get("partial_words", False):
            self.recognizer.SetPartialWords(True)

        max_alternatives = options.get("max_alternatives", 0)
        if max_alternatives > 1:
            self.recognizer.SetMaxAlternatives(max_alternatives)

    def accept_waveform(self, data: bytes) -> bool:
        """Process audio data.

        Args:
            data: Audio data as bytes (int16 PCM format)

        Returns:
            True if final result is ready, False for partial result
        """
        return self.recognizer.AcceptWaveform(data)

    def get_result(self) -> RecognitionResult:
        """Get final recognition result.

        Returns:
            RecognitionResult with final transcription
        """
        result_json = self.recognizer.Result()
        result_dict = json.loads(result_json)

        return self._convert_vosk_result(result_dict, is_partial=False)

    def get_partial_result(self) -> RecognitionResult:
        """Get partial recognition result.

        Returns:
            RecognitionResult with partial transcription
        """
        result_json = self.recognizer.PartialResult()
        result_dict = json.loads(result_json)

        # Vosk partial results have "partial" field instead of "text"
        text = result_dict.get("partial", "")

        return RecognitionResult(
            text=text,
            is_partial=True,
            confidence=1.0,  # Vosk doesn't provide confidence for partials
            words=result_dict.get("result"),  # May have word-level data
            alternatives=None,
        )

    def get_final_result(self) -> RecognitionResult:
        """Get final result and flush any pending audio.

        Returns:
            RecognitionResult with final transcription
        """
        result_json = self.recognizer.FinalResult()
        result_dict = json.loads(result_json)

        return self._convert_vosk_result(result_dict, is_partial=False)

    def reset(self):
        """Reset recognizer state for next utterance."""
        self.recognizer.Reset()

    def set_grammar(self, grammar: str | None):
        """Set grammar/constraints.

        Note: Vosk requires grammar to be set at initialization.
        This method will recreate the recognizer with new grammar.

        Args:
            grammar: JSON array grammar specification, or None to disable
        """
        # Recreate recognizer with new grammar
        if grammar:
            self.recognizer = vosk.KaldiRecognizer(
                self.model, self.sample_rate, grammar
            )
        else:
            self.recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)

        # Reapply options
        if self.options.get("words", False):
            self.recognizer.SetWords(True)

        if self.options.get("partial_words", False):
            self.recognizer.SetPartialWords(True)

        max_alternatives = self.options.get("max_alternatives", 0)
        if max_alternatives > 1:
            self.recognizer.SetMaxAlternatives(max_alternatives)

    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "vosk"

    @property
    def supports_partial_results(self) -> bool:
        """Check if backend supports partial results."""
        return True

    @property
    def supports_grammar(self) -> bool:
        """Check if backend supports grammar constraints."""
        return True

    def _convert_vosk_result(
        self, result_dict: dict, is_partial: bool
    ) -> RecognitionResult:
        """Convert Vosk result dictionary to RecognitionResult.

        Args:
            result_dict: Vosk result dictionary
            is_partial: Whether this is a partial result

        Returns:
            RecognitionResult object
        """
        text = result_dict.get("text", "")
        confidence = result_dict.get("confidence", 1.0)
        words = result_dict.get("result")  # Word-level timestamps
        alternatives = result_dict.get("alternatives")  # Alternative transcriptions

        return RecognitionResult(
            text=text,
            is_partial=is_partial,
            confidence=confidence,
            words=words,
            alternatives=alternatives,
        )
