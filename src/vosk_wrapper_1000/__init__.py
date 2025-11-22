"""
Vosk Simple - A Python wrapper for Vosk speech recognition.

This package provides a simple interface to Vosk speech recognition
with support for audio recording, processing, and model management.
"""

__version__ = "0.1.0"
__author__ = "Vosk Simple Contributors"

from .audio_backend import AudioBackend
from .audio_processor import AudioProcessor
from .audio_recorder import AudioRecorder
from .device_manager import DeviceManager
from .download_model import main as download_model_main
from .hook_manager import HookManager
from .main import main
from .model_manager import ModelManager
from .pid_manager import list_instances, remove_pid, send_signal_to_instance, write_pid
from .signal_manager import SignalManager
from .xdg_paths import get_default_model_path, get_models_dir

__all__ = [
    "AudioBackend",
    "AudioProcessor",
    "AudioRecorder",
    "DeviceManager",
    "HookManager",
    "ModelManager",
    "SignalManager",
    "download_model_main",
    "get_default_model_path",
    "get_models_dir",
    "list_instances",
    "main",
    "remove_pid",
    "send_signal_to_instance",
    "write_pid",
]
