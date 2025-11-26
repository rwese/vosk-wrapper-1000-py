"""Recognition backend implementations."""

from .vosk_backend import VoskBackend

# Optional backends (imported only if dependencies available)
try:
    from .faster_whisper_backend import FasterWhisperBackend

    __all__ = ["FasterWhisperBackend", "VoskBackend"]
except ImportError:
    __all__ = ["VoskBackend"]
