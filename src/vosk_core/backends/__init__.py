"""Recognition backend implementations."""

from .vosk_backend import VoskBackend

# Optional backends (imported only if dependencies available)
try:
    from .faster_whisper_backend import FasterWhisperBackend

    __all__ = ["FasterWhisperBackend", "VoskBackend"]
except ImportError:
    __all__ = ["VoskBackend"]

try:
    from .whisper_backend import WhisperBackend

    if "WhisperBackend" not in __all__:
        __all__.append("WhisperBackend")
except ImportError:
    pass
