"""
Vosk Simple - A Python wrapper for Vosk speech recognition.

This package provides a simple interface to Vosk speech recognition
with support for audio recording, processing, and model management.
"""

__version__ = "0.1.0"
__author__ = "Vosk Simple Contributors"

from vosk_core.audio_backend import AudioBackend
from vosk_core.audio_processor import AudioProcessor
from vosk_core.audio_recorder import AudioRecorder
from vosk_core.device_manager import DeviceManager
from vosk_core.download_model import main as download_model_main
from .hook_manager import HookManager
from .ipc_client import IPCClient
from .ipc_server import IPCServer
from .main import main
from vosk_core.model_manager import ModelManager
from .pid_manager import list_instances, remove_pid, send_signal_to_instance, write_pid
from .signal_manager import SignalManager
from vosk_core.xdg_paths import get_default_model_path, get_models_dir

__all__ = [
    "AudioBackend",
    "AudioProcessor",
    "AudioRecorder",
    "DeviceManager",
    "HookManager",
    "IPCClient",
    "IPCServer",
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
