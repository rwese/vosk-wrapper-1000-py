"""Audio backend abstraction layer for cross-platform support."""

import platform
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable


class AudioBackend(ABC):
    """Abstract base class for audio backends."""

    @abstractmethod
    def create_stream(
        self,
        samplerate: int,
        blocksize: int,
        device: int | None,
        channels: int,
        callback: Callable,
    ) -> bool:
        """
        Create and start an audio input stream.

        Returns:
            bool: True if stream was created successfully, False otherwise
        """
        pass

    @abstractmethod
    def stop_stream(self):
        """Stop and close the audio stream."""
        pass

    @abstractmethod
    def is_active(self) -> bool:
        """Check if stream is active."""
        pass


class SoundDeviceBackend(AudioBackend):
    """Audio backend using sounddevice (works on macOS, Windows, Linux with ALSA/PulseAudio)."""

    def __init__(self):
        import sounddevice as sd

        self.sd = sd
        self.stream = None
        self._creation_thread = None

    def create_stream(
        self,
        samplerate: int,
        blocksize: int,
        device: int | None,
        channels: int,
        callback: Callable,
    ) -> bool:
        """Create stream in a background thread to avoid blocking."""
        stream_created = False
        stream_error = None

        def _create():
            nonlocal stream_created, stream_error
            try:
                self.stream = self.sd.RawInputStream(
                    samplerate=samplerate,
                    blocksize=blocksize,
                    device=device,
                    dtype="int16",
                    channels=channels,
                    callback=callback,
                )
                stream_created = True
            except Exception as e:
                stream_error = e
                stream_created = False

        # Create stream in background thread with timeout
        self._creation_thread = threading.Thread(target=_create, daemon=True)
        self._creation_thread.start()
        self._creation_thread.join(timeout=5.0)

        if self._creation_thread.is_alive():
            # Thread still running, stream creation is slow but may succeed
            return False  # Indicates timeout, not failure

        if stream_error:
            raise stream_error

        return stream_created

    def stop_stream(self):
        """Stop and close the stream."""
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def is_active(self) -> bool:
        """Check if stream is active."""
        return self.stream is not None and self.stream.active


class PipeWireBackend(AudioBackend):
    """Audio backend using pipewire-python (Linux with PipeWire)."""

    def __init__(self):
        try:
            from pipewire_python.controller import Controller

            self.Controller = Controller
            self.controller = None
            self._recording_thread = None
            self._stop_recording = threading.Event()
        except ImportError as err:
            raise ImportError(
                "pipewire-python is not installed. Install with: pip install pipewire-python"
            ) from err

    def create_stream(
        self,
        samplerate: int,
        blocksize: int,
        device: int | None,
        channels: int,
        callback: Callable,
    ) -> bool:
        """Create PipeWire recording stream."""
        # PipeWire-python uses a different API - we'll need to adapt it
        # For now, raise NotImplementedError as this needs more work
        raise NotImplementedError("PipeWire backend is not yet fully implemented")

    def stop_stream(self):
        """Stop PipeWire recording."""
        if self._recording_thread:
            self._stop_recording.set()
            self._recording_thread.join(timeout=2.0)
            self._recording_thread = None

    def is_active(self) -> bool:
        """Check if recording is active."""
        return self._recording_thread is not None and self._recording_thread.is_alive()


def get_audio_backend() -> AudioBackend:
    """
    Get the appropriate audio backend for the current platform.

    Returns:
        AudioBackend: The audio backend instance
    """
    system = platform.system()

    # Try to detect PipeWire on Linux
    if system == "Linux":
        try:
            # Check if PipeWire is running
            import subprocess

            result = subprocess.run(
                ["pgrep", "-x", "pipewire"], capture_output=True, text=True
            )
            if result.returncode == 0:
                # PipeWire is running, but we'll still use SoundDevice for now
                # since PipeWire backend isn't fully implemented
                pass
        except Exception:
            pass

    # For now, always use SoundDevice backend (works cross-platform)
    return SoundDeviceBackend()
