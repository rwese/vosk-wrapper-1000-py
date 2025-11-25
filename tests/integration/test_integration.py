import json
import os
import sys
from unittest.mock import MagicMock, patch, ANY

import numpy as np
import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vosk_wrapper_1000.main import run_service


class MockArgs:
    def __init__(self):
        self.name = "test_instance"
        self.model = "mock_model_path"
        self.device = None
        self.samplerate = 16000
        self.hooks_dir = "/tmp/hooks"
        self.list_devices = False
        self.disable_noise_filter = True
        self.disable_noise_reduction = True  # Updated attribute name
        self.noise_reduction_level = 0.2  # Updated attribute name
        self.stationary_noise = True
        self.non_stationary_noise = False
        self.noise_reduction_min_rms_ratio = 0.5
        self.silence_threshold = 50.0
        self.vad_hysteresis = 10
        self.pre_roll_duration = 2.0
        self.normalize_audio = False
        self.normalize_target_level = 0.3
        self.record_audio = None
        self.auto_start = True  # Enable auto-start for testing
        self.words = False
        self.partial_words = False
        self.grammar = None


@pytest.fixture
def mock_vosk():
    mock_model = MagicMock()
    mock_rec = MagicMock()
    mock_rec.AcceptWaveform.return_value = True
    mock_rec.Result.return_value = json.dumps({"text": "hello world"})

    mock_module = MagicMock()
    mock_module.Model.return_value = mock_model
    mock_module.KaldiRecognizer.return_value = mock_rec

    with patch.dict(sys.modules, {"vosk": mock_module}):
        yield mock_module


@pytest.fixture
def mock_sounddevice():
    mock_sd = MagicMock()
    with patch.dict(sys.modules, {"sounddevice": mock_sd}):
        yield mock_sd


@pytest.fixture
def mock_managers():
    with patch("vosk_wrapper_1000.main.SignalManager") as mock_sm_cls, patch(
        "vosk_wrapper_1000.main.ModelManager"
    ) as mock_mm_cls, patch(
        "vosk_wrapper_1000.main.DeviceManager"
    ) as mock_dm_cls, patch("vosk_wrapper_1000.main.HookManager") as mock_hm_cls, patch(
        "vosk_wrapper_1000.main.write_pid"
    ), patch("vosk_wrapper_1000.main.remove_pid"):
        # Setup SignalManager
        mock_sm = mock_sm_cls.return_value
        # Run a few loops then stop
        # We need enough True values for the loop, and then False values for termination checks
        mock_sm.is_running.side_effect = [True, True, True, False, False, False, False]
        mock_sm.is_listening.return_value = True  # Always listening for this test

        # Setup ModelManager
        mock_mm = mock_mm_cls.return_value
        mock_mm.get_model_sample_rate.return_value = 16000

        # Setup DeviceManager
        mock_dm = mock_dm_cls.return_value
        mock_dm.get_device_info.return_value = {
            "id": 1,
            "name": "Mock Device",
            "max_input_channels": 2,
            "max_output_channels": 0,
            "default_samplerate": 16000,
            "host_api": "Mock API",
        }
        mock_dm.validate_device_for_model.return_value = (True, "OK")

        yield mock_sm, mock_mm, mock_dm, mock_hm_cls.return_value


def test_service_flow(mock_vosk, mock_sounddevice, mock_managers, capsys):
    import queue

    _mock_sm, _mock_mm, _mock_dm, mock_hm = mock_managers

    # Setup InputStream mock to simulate callback
    mock_stream = MagicMock()
    mock_sounddevice.InputStream.return_value = mock_stream

    # Mock the audio queue to simulate processed audio data
    with patch("vosk_wrapper_1000.main.queue.Queue") as mock_queue_class:
        mock_audio_queue = MagicMock()
        mock_queue_class.return_value = mock_audio_queue

        # Simulate audio data being available in the queue
        mock_audio_queue.get.side_effect = [
            b"fake_audio_data",  # First get call returns audio data
            queue.Empty(),  # Subsequent calls raise Empty to exit loop
            queue.Empty(),
        ]

        # Setup Vosk recognizer mock to return "hello world"
        mock_rec = mock_vosk.KaldiRecognizer.return_value
        mock_rec.AcceptWaveform.return_value = True
        mock_rec.Result.return_value = json.dumps({"text": "hello world"})

        # We need to capture callback passed to InputStream
        captured_callback = []

        def side_effect(*args, **kwargs):
            callback = kwargs.get("callback")
            if callback:
                captured_callback.append(callback)
            return mock_stream

        mock_sounddevice.InputStream.side_effect = side_effect

        # Run service
        args = MockArgs()
        run_service(args)

    # Verify interactions
    mock_vosk.Model.assert_called()
    mock_vosk.KaldiRecognizer.assert_called()
    mock_sounddevice.InputStream.assert_called()
    mock_stream.start.assert_called_once()

    # Verify output
    captured = capsys.readouterr()
    assert "hello world" in captured.out

    # Verify hooks - at minimum start should be called
    assert mock_hm.run_hooks.call_count >= 1, "No hooks were called"

    # Check that start hook was called (with any parameters)
    start_calls = [
        call for call in mock_hm.run_hooks.call_args_list if call[0][0] == "start"
    ]
    assert len(start_calls) >= 1, "Start hook was not called"
