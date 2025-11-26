"""Backend factory for creating recognition backend instances."""

from .recognition_backend import RecognitionBackend

# Backend registry will be populated dynamically
BACKEND_REGISTRY: dict[str, type[RecognitionBackend]] = {}


def register_backend(name: str, backend_class: type[RecognitionBackend]):
    """Register a recognition backend.

    Args:
        name: Backend identifier (e.g., 'vosk', 'faster-whisper')
        backend_class: Backend class to register
    """
    BACKEND_REGISTRY[name] = backend_class


def create_backend(
    backend_type: str, model_path: str, sample_rate: int, **options
) -> RecognitionBackend:
    """Create a recognition backend instance.

    Args:
        backend_type: Backend identifier (vosk, faster-whisper, whisper)
        model_path: Path to the recognition model
        sample_rate: Audio sample rate in Hz
        **options: Backend-specific options

    Returns:
        Initialized RecognitionBackend instance

    Raises:
        ValueError: If backend_type is not registered
        ImportError: If required backend library is not installed
    """
    if backend_type not in BACKEND_REGISTRY:
        available = ", ".join(BACKEND_REGISTRY.keys())
        raise ValueError(
            f"Unknown backend: {backend_type}. Available backends: {available}"
        )

    backend_class = BACKEND_REGISTRY[backend_type]

    try:
        return backend_class(model_path, sample_rate, **options)
    except ImportError as e:
        raise ImportError(
            f"Failed to load {backend_type} backend. "
            f"Make sure the required dependencies are installed: {e}"
        ) from e


def list_available_backends() -> list[str]:
    """List all registered backends.

    Returns:
        List of backend identifiers
    """
    return list(BACKEND_REGISTRY.keys())


def is_backend_available(backend_type: str) -> bool:
    """Check if a backend is available.

    Args:
        backend_type: Backend identifier to check

    Returns:
        True if backend is registered
    """
    return backend_type in BACKEND_REGISTRY


# Register built-in backends
def _register_builtin_backends():
    """Register all built-in backends."""
    # Always register Vosk backend (core dependency)
    try:
        from .backends.vosk_backend import VoskBackend

        register_backend("vosk", VoskBackend)
    except ImportError:
        pass  # Vosk not available

    # Try to register FasterWhisper backend (optional)
    try:
        from .backends.faster_whisper_backend import FasterWhisperBackend

        register_backend("faster-whisper", FasterWhisperBackend)
    except ImportError:
        pass  # FasterWhisper not available

    # Try to register Whisper backend (optional)
    try:
        from .backends.whisper_backend import WhisperBackend

        register_backend("whisper", WhisperBackend)
    except ImportError:
        pass  # Whisper not available


# Auto-register backends on module import
_register_builtin_backends()
