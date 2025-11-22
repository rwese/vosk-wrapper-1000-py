"""
Vosk Simple - A Python wrapper for Vosk speech recognition.

This package provides a simple interface to Vosk speech recognition
with support for audio recording, processing, and model management.
"""

__version__ = "0.1.0"
__author__ = "Vosk Simple Contributors"

from .main import main
from .model_manager import ModelManager
from .device_manager import DeviceManager
from .hook_manager import HookManager
from .signal_manager import SignalManager
from .pid_manager import write_pid, remove_pid, list_instances, send_signal_to_instance
from .audio_processor import AudioProcessor
from .audio_recorder import AudioRecorder
from .audio_backend import AudioBackend
from .download_model import main as download_model_main
from .xdg_paths import get_models_dir, get_default_model_path

__all__ = [
    "main",
    "ModelManager",
    "DeviceManager",
    "HookManager",
    "SignalManager",
    "write_pid",
    "remove_pid",
    "list_instances",
    "send_signal_to_instance",
    "AudioProcessor",
    "AudioRecorder",
    "AudioBackend",
    "download_model_main",
    "get_models_dir",
    "get_default_model_path",
]
