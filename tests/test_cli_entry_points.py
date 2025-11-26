"""
E2E tests for CLI entry points to prevent import and packaging regressions.

These tests ensure that all CLI commands can be imported and executed properly,
catching issues like missing modules, broken imports, or incorrect entry point
configurations.
"""

import subprocess
import sys
import unittest


class TestCLIEntryPoints(unittest.TestCase):
    """Test that all CLI entry points can be imported and executed."""

    def test_vosk_wrapper_1000_import(self):
        """Test that vosk-wrapper-1000 entry point can be imported."""
        result = subprocess.run(
            [sys.executable, "-c", "from vosk_wrapper_1000.main import main"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Failed to import vosk_wrapper_1000.main: {result.stderr}",
        )

    def test_vosk_wrapper_1000_help(self):
        """Test that vosk-wrapper-1000 --help works."""
        result = subprocess.run(
            ["vosk-wrapper-1000", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")
        self.assertIn("Vosk Speech Recognition", result.stdout)

    def test_vosk_download_model_import(self):
        """Test that vosk-download-model-1000 entry point can be imported."""
        result = subprocess.run(
            [sys.executable, "-c", "from vosk_core.download_model import main"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Failed to import vosk_core.download_model: {result.stderr}",
        )

    def test_vosk_download_model_help(self):
        """Test that vosk-download-model-1000 --help works."""
        result = subprocess.run(
            ["vosk-download-model-1000", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")
        self.assertIn("Download and manage speech recognition models", result.stdout)

    def test_vosk_transcribe_file_import(self):
        """Test that vosk-transcribe-file entry point can be imported."""
        result = subprocess.run(
            [sys.executable, "-c", "from vosk_transcribe.main import main"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Failed to import vosk_transcribe.main: {result.stderr}",
        )

    def test_vosk_transcribe_file_help(self):
        """Test that vosk-transcribe-file --help works."""
        result = subprocess.run(
            ["vosk-transcribe-file", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")
        self.assertIn("Transcribe audio files", result.stdout)

    def test_vosk_settings_tui_import(self):
        """Test that vosk-settings-tui entry point can be imported."""
        result = subprocess.run(
            [sys.executable, "-c", "from vosk_wrapper_1000.settings_tui import main"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Failed to import vosk_wrapper_1000.settings_tui: {result.stderr}",
        )

    def test_vosk_audio_monitor_import(self):
        """Test that vosk-audio-monitor entry point can be imported."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from vosk_wrapper_1000.audio_monitor import main",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Failed to import vosk_wrapper_1000.audio_monitor: {result.stderr}",
        )

    def test_all_entry_points_in_package(self):
        """Test that all entry points defined in pyproject.toml can be imported."""
        # This test ensures that if we add new entry points, we catch import errors
        entry_points = {
            "vosk-wrapper-1000": "vosk_wrapper_1000.main:main",
            "vosk-download-model-1000": "vosk_core.download_model:main",
            "vosk-transcribe-file": "vosk_transcribe.main:main",
            "vosk-settings-tui": "vosk_wrapper_1000.settings_tui:main",
            "vosk-audio-monitor": "vosk_wrapper_1000.audio_monitor:main",
        }

        for cmd_name, module_path in entry_points.items():
            with self.subTest(entry_point=cmd_name):
                module, func = module_path.split(":")
                result = subprocess.run(
                    [sys.executable, "-c", f"from {module} import {func}"],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"Failed to import {module_path} for {cmd_name}: {result.stderr}",
                )

    def test_package_imports(self):
        """Test that the main package can be imported with all expected exports."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
from vosk_wrapper_1000 import (
    AudioBackend,
    AudioProcessor,
    AudioRecorder,
    DeviceManager,
    HookManager,
    IPCClient,
    IPCServer,
    ModelManager,
    SignalManager,
    download_model_main,
    get_default_model_path,
    get_models_dir,
    list_instances,
    main,
    remove_pid,
    send_signal_to_instance,
    write_pid,
)
print("All imports successful")
""",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0, f"Package import failed: {result.stderr}"
        )
        self.assertIn("All imports successful", result.stdout)


if __name__ == "__main__":
    unittest.main()
