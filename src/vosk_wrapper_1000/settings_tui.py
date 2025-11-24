#!/usr/bin/env python3
"""Interactive TUI for experimenting with vosk-wrapper-1000 audio processing settings."""

import queue
import sys
import threading
from pathlib import Path
from typing import Optional

import numpy as np
import yaml
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    Select,
    Static,
)

from vosk_core.audio_processor import AudioProcessor
from vosk_core.device_manager import DeviceManager
from vosk_core.model_manager import ModelManager
from vosk_core.xdg_paths import XDGPaths


class AudioMonitor(Static):
    """Widget displaying real-time audio levels and gate status."""

    DEFAULT_CSS = """
    AudioMonitor {
        height: auto;
        padding: 1;
        border: solid $accent;
        background: $panel;
        margin: 1 0;
    }

    #audio-level-bar {
        height: 2;
        margin: 1 0;
    }

    .monitor-label {
        color: $text;
        text-style: bold;
    }

    .monitor-value {
        color: $accent;
    }

    .gate-open {
        color: green;
        text-style: bold;
    }

    .gate-closed {
        color: red;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the compact audio monitor UI."""
        yield Static("🎙️ VAD Monitor", classes="monitor-label")
        yield Static(
            "Raw RMS: 0.0 | VAD: CLOSED", id="status-line", classes="monitor-value"
        )
        yield ProgressBar(total=100, show_eta=False, id="audio-level-bar")

    def update_rms(self, rms: float) -> None:
        """Update the compact status line with RMS and VAD info."""
        status_line = self.query_one("#status-line", Static)
        current_text = status_line.renderable.plain
        # Extract VAD part and update RMS part
        if " | VAD:" in current_text:
            vad_part = current_text.split(" | VAD:")[1]
            status_line.update(f"Raw RMS: {rms:.1f} | VAD: {vad_part}")
        else:
            status_line.update(f"Raw RMS: {rms:.1f} | VAD: CLOSED")

    def update_vad_status(
        self, is_in_speech: bool, consecutive_silent: int, chunks_returned: int
    ) -> None:
        """Update VAD status in the compact display."""
        status_line = self.query_one("#status-line", Static)
        current_text = status_line.renderable.plain

        if is_in_speech:
            vad_status = f"OPEN ✓ ({chunks_returned})"
        else:
            vad_status = f"CLOSED ✗ ({consecutive_silent})"

        # Extract RMS part and update VAD part
        if "Raw RMS:" in current_text:
            rms_part = current_text.split(" | VAD:")[0]
            status_line.update(f"{rms_part} | VAD: {vad_status}")
        else:
            status_line.update(f"Raw RMS: 0.0 | VAD: {vad_status}")

    def update_monitoring(self, monitoring: bool) -> None:
        """Update monitoring status - no longer used in compact layout."""
        pass


class SettingsPanel(VerticalScroll):
    """Scrollable panel containing all audio processing settings."""

    def on_mount(self) -> None:
        """Called when the panel is mounted."""
        pass

    DEFAULT_CSS = """
    SettingsPanel {
        height: 100%;
        padding: 1;
    }

    .setting-row {
        height: 3;
        margin: 0 0 1 0;
        align: left middle;
    }

    .setting-label {
        width: 25;
        height: auto;
        color: $text;
        text-style: bold;
    }

    .setting-input {
        width: 35;
        height: auto;
    }

    .wide-input {
        width: 50;
        height: auto;
    }

    .compact-checkbox {
        margin: 0 1;
    }

    Select {
        max-width: 50;
    }

    Select .select--label {
        text-overflow: ellipsis;
        overflow: hidden;
    }
    """

    def __init__(self, initial_settings: dict, **kwargs):
        super().__init__(**kwargs)
        self.settings = initial_settings

    def compose(self) -> ComposeResult:
        """Compose the compact settings panel UI."""
        audio_settings = self.settings["audio"]
        model_settings = self.settings["model"]

        # Model and Device Selection Row
        with Horizontal(classes="setting-row"):
            yield Label("Model:", classes="setting-label")
            # Get available models
            model_manager = ModelManager()
            available_models = model_manager.list_available_models()
            current_model = model_settings.get("path", "")

            # Create options for the select widget
            options = [("None", None)]
            for model_name in available_models:
                model_path = str(model_manager.models_dir / model_name)
                options.append((model_name, model_path))

            # Convert current_model to full path if it's a model name
            current_model_path = None
            if current_model:
                try:
                    current_model_path = str(
                        model_manager.resolve_model_path(current_model)
                    )
                except FileNotFoundError:
                    # Model not found, will default to None
                    pass

            yield Select(
                options=options,
                value=current_model_path,
                id="model_path",
                classes="wide-input",
            )

        with Horizontal(classes="setting-row"):
            yield Label("Device:", classes="setting-label")
            # Get available devices
            device_manager = DeviceManager()
            available_devices = device_manager.refresh_devices()
            current_device = audio_settings.get("default_device", "")

            # Create options for the select widget
            options = [("System Default", "")]
            for device in available_devices:
                device_label = f"{device['name']} (ID: {device['id']})"
                device_value = str(device["id"])  # Store as string for Select widget
                options.append((device_label, device_value))

            yield Select(
                options=options,
                value=current_device,
                id="default_device",
                classes="wide-input",
            )

        # Audio Monitor Section
        yield AudioMonitor(id="audio-monitor")

        # Compact settings rows
        with Horizontal(classes="setting-row"):
            yield Label("Noise Red.:", classes="setting-label")
            yield Checkbox(
                value=audio_settings.get("noise_reduction_enabled", True),
                id="noise_reduction_enabled",
                classes="compact-checkbox",
            )
            yield Input(
                value=str(audio_settings.get("noise_reduction_level", 0.05)),
                placeholder="0.0-1.0",
                id="noise_reduction_level",
                classes="setting-input",
            )
            yield Checkbox(
                value=audio_settings.get("stationary_noise", False),
                id="stationary_noise",
                classes="compact-checkbox",
            )

        with Horizontal(classes="setting-row"):
            yield Label("Silence Thr.:", classes="setting-label")
            yield Input(
                value=str(audio_settings.get("silence_threshold", 50.0)),
                placeholder="RMS",
                id="silence_threshold",
                classes="setting-input",
            )
            yield Label("VAD Hyst.:", classes="setting-label")
            yield Input(
                value=str(audio_settings.get("vad_hysteresis_chunks", 10)),
                placeholder="Chunks",
                id="vad_hysteresis_chunks",
                classes="setting-input",
            )

        with Horizontal(classes="setting-row"):
            yield Label("Pre-roll:", classes="setting-label")
            yield Input(
                value=str(audio_settings.get("pre_roll_duration", 0.5)),
                placeholder="Seconds",
                id="pre_roll_duration",
                classes="setting-input",
            )
            yield Label("Normalize:", classes="setting-label")
            yield Checkbox(
                value=audio_settings.get("normalize_audio", False),
                id="normalize_audio",
                classes="compact-checkbox",
            )
            yield Input(
                value=str(audio_settings.get("normalization_target_level", 0.3)),
                placeholder="0.0-1.0",
                id="normalization_target_level",
                classes="setting-input",
            )


class SettingsTUI(App):
    """Interactive TUI for audio processing settings."""

    CSS = """
    Screen {
        background: $surface;
    }

    #button-row {
        height: auto;
        margin: 1 2;
        align: center middle;
    }

    Button {
        margin: 0 1;
        min-width: 20;
    }


    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "save", "Save"),
        ("r", "reset", "Reset"),
        ("m", "toggle_monitor", "Monitor"),
    ]

    def __init__(self, config_path: Optional[Path] = None):
        super().__init__()
        xdg = XDGPaths()
        self.config_path = config_path or (xdg.get_config_dir() / "config.yaml")
        self.title = "Vosk Audio Processing Settings"
        self.sub_title = f"Config: {self.config_path}"

        # Audio monitoring state
        self.audio_stream = None
        self.monitor_thread = None
        self.monitor_queue = queue.Queue()
        self.monitoring = False

        # Load settings
        self.settings = self._load_current_settings()

    def _load_current_settings(self) -> dict:
        """Load current settings from config file or return defaults."""
        # Default settings
        defaults = {
            "audio": {
                "default_device": "",
                "noise_reduction_enabled": True,
                "noise_reduction_level": 0.05,
                "stationary_noise": False,
                "silence_threshold": 50.0,
                "normalize_audio": False,
                "normalization_target_level": 0.3,
                "vad_hysteresis_chunks": 10,
                "pre_roll_duration": 0.5,
                "noise_reduction_min_rms_ratio": 0.5,
            },
            "model": {
                "path": None,
            },
        }

        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    loaded = yaml.safe_load(f) or {}
                    # Merge with defaults
                    if "audio" in loaded:
                        defaults["audio"].update(loaded["audio"])
                    if "model" in loaded:
                        defaults["model"].update(loaded["model"])
            except Exception as e:
                print(f"Warning: Could not load config: {e}", file=sys.stderr)

        return defaults

    def compose(self) -> ComposeResult:
        """Compose the application UI."""
        yield Header()
        yield SettingsPanel(initial_settings=self.settings)

        with Horizontal(id="button-row"):
            yield Button("🎙️ Start Monitor", variant="success", id="monitor-btn")
            yield Button("💾 Save Settings", variant="primary", id="save-btn")
            yield Button("🔄 Reset to Defaults", variant="warning", id="reset-btn")
            yield Button("❌ Quit", variant="error", id="quit-btn")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            self.action_save()
        elif event.button.id == "reset-btn":
            self.action_reset()
        elif event.button.id == "monitor-btn":
            self.action_toggle_monitor()
        elif event.button.id == "quit-btn":
            self.action_quit()

    def action_save(self) -> None:
        """Save current settings to config file."""
        try:
            settings = self._collect_settings()
            self._save_to_file(settings)
            self._update_status("✅ Settings saved successfully!", "green")
        except Exception as e:
            self._update_status(f"❌ Error saving settings: {e}", "red")

    def action_reset(self) -> None:
        """Reset settings to defaults."""
        self._update_status("🔄 Resetting to defaults...", "yellow")
        # Reload with defaults
        self.settings = self._load_current_settings()
        # Remove and recreate settings panel
        settings_panel = self.query_one(SettingsPanel)
        settings_panel.remove()
        new_panel = SettingsPanel(initial_settings=self.settings)
        self.mount(new_panel, before=self.query_one("#button-row"))
        self._update_status("✅ Reset to defaults", "green")

    def action_toggle_monitor(self) -> None:
        """Toggle audio monitoring on/off."""
        if not self.monitoring:
            self._start_monitoring()
        else:
            self._stop_monitoring()

    def _start_monitoring(self) -> None:
        """Start real-time audio monitoring."""
        try:
            import sounddevice as sd

            # Get current settings
            settings = self._collect_settings()
            audio_settings = settings["audio"]

            # Create AudioProcessor with same settings as daemon
            self.audio_processor = AudioProcessor(
                device_rate=16000,  # Will be updated after device detection
                model_rate=16000,  # Use 16kHz for VAD (matches Vosk models)
                noise_filter_enabled=audio_settings.get(
                    "noise_reduction_enabled", True
                ),
                noise_reduction_strength=audio_settings.get(
                    "noise_reduction_level", 0.05
                ),
                stationary_noise=audio_settings.get("stationary_noise", False),
                silence_threshold=audio_settings.get("silence_threshold", 50.0),
                normalize_audio=audio_settings.get("normalize_audio", False),
                normalization_target_level=audio_settings.get(
                    "normalization_target_level", 0.3
                ),
                pre_roll_duration=audio_settings.get("pre_roll_duration", 0.5),
                vad_hysteresis_chunks=audio_settings.get("vad_hysteresis_chunks", 10),
                noise_reduction_min_rms_ratio=audio_settings.get(
                    "noise_reduction_min_rms_ratio", 0.5
                ),
            )

            self.monitoring = True

            # Update button
            try:
                btn = self.query_one("#monitor-btn", Button)
                btn.label = "⏹️ Stop Monitor"
                btn.variant = "error"
            except Exception:
                pass  # Button might not be mounted yet

            # Update monitor widget
            try:
                monitor = self.query_one("#audio-monitor", AudioMonitor)
                monitor.update_monitoring(True)
            except Exception:
                pass  # Monitor might not be mounted yet

            # Get device info for configured device or fallback to system default
            device_manager = DeviceManager()
            configured_device = audio_settings.get("default_device", "")

            device_id = None
            device_rate = 48000  # Default fallback rate

            if configured_device:
                # Try to use configured device
                device_info = device_manager.get_device_info(configured_device)
                if device_info:
                    device_id = device_info["id"]
                    device_rate = int(device_info["default_samplerate"])
                else:
                    print(
                        f"Warning: Configured device '{configured_device}' not found, using system default",
                        file=sys.stderr,
                    )

            # If no configured device or configured device not found, use system default
            if device_id is None:
                try:
                    default_device = sd.query_devices(kind="input")
                    device_rate = int(default_device["default_samplerate"])
                except Exception:
                    device_rate = 48000  # Fallback to common rate

            # Update AudioProcessor with actual device rate
            self.audio_processor.device_rate = device_rate
            self.audio_processor.model_rate = 16000  # Use 16kHz for VAD

            # Initialize resampler if needed
            if device_rate != 16000:
                import soxr

                self.audio_processor.soxr_resampler = soxr.ResampleStream(
                    in_rate=device_rate, out_rate=16000, num_channels=1, quality="HQ"
                )

            def audio_callback(indata, frames, time, status):
                """Process audio data in callback."""
                if status:
                    print(status, file=sys.stderr)

                # Convert to numpy array
                audio_data = np.frombuffer(indata, dtype=np.int16)

                # Use AudioProcessor VAD logic (same as daemon)
                audio_chunks = self.audio_processor.process_with_vad(audio_data)

                # Get current speech state
                is_in_speech = self.audio_processor.in_speech
                consecutive_silent = self.audio_processor.consecutive_silent_chunks

                # Calculate RMS of raw audio for display
                if len(audio_data.shape) > 1:
                    audio_data = np.mean(audio_data, axis=1).astype(np.int16)
                audio_float = audio_data.astype(np.float32)
                audio_float = audio_float - np.mean(audio_float)
                rms = float(np.sqrt(np.mean(audio_float**2)))

                # Send to UI thread: (rms, is_in_speech, consecutive_silent, chunks_returned)
                try:
                    self.monitor_queue.put_nowait(
                        (rms, is_in_speech, consecutive_silent, len(audio_chunks))
                    )
                except queue.Full:
                    pass

            # Start audio stream with device's native sample rate
            self.audio_stream = sd.RawInputStream(
                samplerate=device_rate,
                blocksize=1024,
                device=device_id,
                dtype="int16",
                channels=1,
                callback=audio_callback,
            )
            self.audio_stream.start()

            # Start UI update thread
            self.monitor_thread = threading.Thread(target=self._update_monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()

            self._update_status("🎙️ Audio monitoring started", "green")

        except Exception as e:
            self._update_status(f"❌ Error starting monitor: {e}", "red")
            self.monitoring = False

    def _stop_monitoring(self) -> None:
        """Stop real-time audio monitoring."""
        self.monitoring = False

        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None

        # Reset VAD state for next monitoring session
        if hasattr(self, "audio_processor"):
            self.audio_processor.reset_vad_state()

        # Update button
        try:
            btn = self.query_one("#monitor-btn", Button)
            btn.label = "🎙️ Start Monitor"
            btn.variant = "success"
        except Exception:
            pass  # Button might not be mounted

        # Update monitor widget
        try:
            monitor = self.query_one("#audio-monitor", AudioMonitor)
            monitor.update_monitoring(False)
        except Exception:
            pass  # Monitor might not be mounted

        try:
            self._update_status("⏹️ Audio monitoring stopped", "yellow")
        except Exception:
            pass  # Status might not be mounted

    def _update_monitor_loop(self) -> None:
        """Update monitor display from queue."""
        while self.monitoring:
            try:
                rms, is_in_speech, consecutive_silent, chunks_returned = (
                    self.monitor_queue.get(timeout=0.1)
                )
                try:
                    monitor = self.query_one("#audio-monitor", AudioMonitor)
                    monitor.update_rms(rms)
                    monitor.update_vad_status(
                        is_in_speech, consecutive_silent, chunks_returned
                    )
                except Exception:
                    pass  # Monitor might not be mounted
            except queue.Empty:
                continue
            except Exception:
                break

    def _collect_settings(self) -> dict:
        """Collect current settings from UI inputs."""
        settings = {"audio": {}, "model": {}}

        # Collect checkbox values
        for field_id in [
            "noise_reduction_enabled",
            "stationary_noise",
            "normalize_audio",
        ]:
            try:
                widget = self.query_one(f"#{field_id}", Checkbox)
                settings["audio"][field_id] = widget.value
            except Exception:
                # Keep existing value if collection fails
                if field_id in self.settings["audio"]:
                    settings["audio"][field_id] = self.settings["audio"][field_id]

        # Collect numeric input values
        numeric_fields = {
            "noise_reduction_level": float,
            "silence_threshold": float,
            "vad_hysteresis_chunks": int,
            "pre_roll_duration": float,
            "noise_reduction_min_rms_ratio": float,
            "normalization_target_level": float,
        }

        for field_id, converter in numeric_fields.items():
            try:
                widget = self.query_one(f"#{field_id}", Input)
                value = converter(widget.value)
                settings["audio"][field_id] = value
            except (ValueError, Exception):
                # Keep existing value if parsing fails
                if field_id in self.settings["audio"]:
                    settings["audio"][field_id] = self.settings["audio"][field_id]

        # Collect model selection
        try:
            model_select = self.query_one("#model_path", Select)
            selected_value = model_select.value
            settings["model"]["path"] = selected_value
        except Exception:
            # Keep existing value if selection fails
            if "model" in self.settings and "path" in self.settings["model"]:
                settings["model"]["path"] = self.settings["model"]["path"]

        # Collect device selection
        try:
            device_select = self.query_one("#default_device", Select)
            selected_value = device_select.value
            settings["audio"]["default_device"] = selected_value
        except Exception:
            # Keep existing value if selection fails
            if "default_device" in self.settings["audio"]:
                settings["audio"]["default_device"] = self.settings["audio"][
                    "default_device"
                ]

        return settings

    def _save_to_file(self, settings: dict) -> None:
        """Save settings to YAML config file."""
        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config if it exists
        existing_config = {}
        if self.config_path.exists():
            with open(self.config_path) as f:
                existing_config = yaml.safe_load(f) or {}

        # Merge settings (preserve other sections)
        existing_config["audio"] = settings["audio"]
        existing_config["model"] = settings["model"]

        # Write updated config
        yaml_output = yaml.dump(
            existing_config, default_flow_style=False, sort_keys=False
        )

        with open(self.config_path, "w") as f:
            f.write(yaml_output)

    def _update_status(self, message: str, color: str = "white") -> None:
        """Show a toast notification."""
        # Map colors to severity levels
        severity_map = {
            "green": "information",
            "red": "error",
            "yellow": "warning",
            "white": "information",
        }
        severity = severity_map.get(color, "information")

        # Clean up emoji and extra formatting for toast
        clean_message = (
            message.replace("✅ ", "")
            .replace("❌ ", "")
            .replace("🔄 ", "")
            .replace("🎙️ ", "")
            .replace("⏹️ ", "")
        )

        self.notify(clean_message, severity=severity, timeout=3)

    def on_unmount(self) -> None:
        """Clean up when app closes."""
        self._stop_monitoring()


def main():
    """Run the settings TUI application."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Interactive TUI for vosk-wrapper-1000 audio processing settings"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config file (default: ~/.config/vosk-wrapper-1000/config.yaml)",
    )

    args = parser.parse_args()

    app = SettingsTUI(config_path=args.config)
    app.run()


if __name__ == "__main__":
    main()
