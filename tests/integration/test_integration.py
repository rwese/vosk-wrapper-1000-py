import json
import os
import sys
from unittest.mock import MagicMock, patch

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
        self.noise_reduction = 0.2
        self.stationary_noise = True
        self.non_stationary_noise = False
        self.record_audio = None
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
    ) as mock_mm_cls, patch("vosk_wrapper_1000.main.DeviceManager") as mock_dm_cls, patch(
        "vosk_wrapper_1000.main.HookManager"
    ) as mock_hm_cls, patch(
        "vosk_wrapper_1000.main.write_pid"
    ), patch(
        "vosk_wrapper_1000.main.remove_pid"
    ):
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
    mock_sm, mock_mm, mock_dm, mock_hm = mock_managers

    # Setup InputStream mock to simulate callback
    mock_stream = MagicMock()
    mock_sounddevice.InputStream.return_value = mock_stream

    # We need to capture the callback passed to InputStream
    def side_effect(*args, **kwargs):
        callback = kwargs.get("callback")
        if callback:
            # Simulate audio data
            # indata, frames, time, status
            data = np.zeros((1024, 1), dtype="float32")
            callback(data, 1024, None, None)
        return mock_stream

    mock_sounddevice.InputStream.side_effect = side_effect

    # Run service
    args = MockArgs()
    run_service(args)

    # Verify interactions
    mock_vosk.Model.assert_called()
    mock_vosk.KaldiRecognizer.assert_called()
    mock_sounddevice.InputStream.assert_called()
    mock_stream.start.assert_not_called()  # It might be called implicitly or explicitly?
    # main.py doesn't call stream.start(), InputStream starts automatically by default?
    # Wait, main.py: stream = sd.InputStream(...) -> context manager? No, just assignment.
    # It doesn't call start() explicitly?
    # Checking main.py:
    # stream = sd.InputStream(...)
    # It does NOT call stream.start(). sd.InputStream starts by default unless start=False.

    # Verify output
    captured = capsys.readouterr()
    assert "hello world" in captured.out

    # Verify hooks
    mock_hm.run_hooks.assert_any_call("start")
    mock_hm.run_hooks.assert_any_call(
        "line", payload="hello world", args=["hello world"]
    )
    # Stop hook might be called when loop ends
    mock_hm.run_hooks.assert_any_call("stop", payload="hello world")
