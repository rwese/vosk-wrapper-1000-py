#!/usr/bin/env python3
"""Live audio monitoring tool for vosk-wrapper-1000.

Allows recording audio, processing it, playing it back, and modifying settings
to re-process with different configurations.
"""

import argparse
import logging
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
import textual.app as textual
import textual.containers as containers
import textual.widgets as widgets
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget

from vosk_core.audio_processor import AudioProcessor
from vosk_core.model_manager import ModelManager
from vosk_wrapper_1000.audio_recorder import AudioRecorder
from vosk_wrapper_1000.config_manager import ConfigManager
from vosk_wrapper_1000.device_manager import DeviceManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler("audio_monitor.log"),
    ],
)
logger = logging.getLogger(__name__)


class WaveformWidget(Widget):
    """Widget for displaying audio waveforms."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.audio_data: Optional[np.ndarray] = None
        self.sample_rate = 16000

    def set_audio_data(self, data: np.ndarray, sample_rate: int):
        """Set the audio data to display."""
        self.audio_data = data
        self.sample_rate = sample_rate
        self.refresh()

    def render(self):
        """Render the waveform."""
        if self.audio_data is None or len(self.audio_data) == 0:
            return "[No audio data]"

        width = self.size.width
        height = self.size.height

        if width <= 2 or height <= 2:
            return "[Too small to display]"

        # Downsample for display
        if len(self.audio_data) > width * 2:
            step = len(self.audio_data) // width
            display_data = self.audio_data[::step][:width]
        else:
            display_data = self.audio_data

        # Normalize to -1 to 1
        if np.max(np.abs(display_data)) > 0:
            display_data = display_data / np.max(np.abs(display_data))

        # Create ASCII waveform
        lines = []
        for row in range(height):
            line = ""
            threshold = (row / height) * 2 - 1  # -1 to 1
            for sample in display_data:
                if abs(sample) >= abs(threshold):
                    line += "│"
                else:
                    line += " "
            lines.append(line)

        return "\n".join(lines)


class AudioMonitorApp(textual.App):
    """Main TUI application for audio monitoring."""

    CSS = """
    #title {
        height: 1;
        text-align: center;
        text-style: bold;
        background: $panel;
    }

    #btn-container {
        height: 3;
        align: center middle;
    }

    #waveform {
        height: 5;
        border: solid $accent;
    }

    #settings {
        height: 13;
        border: solid $primary;
        padding: 0 1;
    }

    #status {
        height: 1;
        background: $boost;
        padding: 0 1;
    }

    Button {
        margin: 0 1;
    }

    Label {
        width: 14;
        text-align: right;
    }

    Horizontal {
        height: auto;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "record", "Record"),
        Binding("space", "toggle_record", "Record/Stop"),
        Binding("p", "playback", "Playback"),
        Binding("s", "save", "Save"),
    ]

    is_recording = reactive(False)
    audio_data: Optional[np.ndarray] = reactive(None)
    current_file: Optional[Path] = reactive(None)

    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.device_manager = DeviceManager()
        self.model_manager = ModelManager()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.recording_stream: Optional[sd.InputStream] = None
        self.playback_stream: Optional[sd.OutputStream] = None
        self.recorder: Optional[AudioRecorder] = None
        self.audio_processor: Optional[AudioProcessor] = None
        self.processed_audio_data: Optional[np.ndarray] = None

    def compose(self):
        """Compose the UI layout."""
        with containers.Vertical():
            yield widgets.Static("Audio Monitor", id="title")
            with containers.Horizontal(id="btn-container"):
                yield widgets.Button("Record", id="record-btn")
                yield widgets.Button("Stop", id="stop-btn")
                yield widgets.Button("Playback", id="playback-btn")
                yield widgets.Button("Save", id="save-btn")
                yield widgets.Button("Clear", id="clear-btn")
            yield WaveformWidget(id="waveform")
            with containers.Vertical(id="settings"):
                yield widgets.Static(" Audio Settings ")
                with containers.Horizontal():
                    yield widgets.Label("Device:")
                    yield widgets.Select(
                        [
                            (
                                str(dev.get("name", f"Device {dev['id']}")),
                                str(dev["id"]),
                            )
                            for dev in self.device_manager.refresh_devices()
                        ],
                        id="device-select",
                        allow_blank=False,
                    )
                with containers.Horizontal():
                    yield widgets.Label("Sample Rate:")
                    yield widgets.Input(value="16000", id="sample-rate-input")
                    yield widgets.Label("Channels:")
                    yield widgets.Select(
                        [("1", "1"), ("2", "2")],
                        value="1",
                        id="channels-select",
                        allow_blank=False,
                    )
                with containers.Horizontal():
                    yield widgets.Label("Buffer Size:")
                    yield widgets.Input(value="1024", id="buffer-size-input")
                    yield widgets.Label("Latency:")
                    yield widgets.Input(value="low", id="latency-input")
            yield widgets.Static("Ready", id="status")

    def on_mount(self):
        """Initialize the app when mounted."""
        logger.info("Audio Monitor starting up")
        logger.info(f"Temporary directory: {self.temp_dir}")
        try:
            self.update_device_list()
            self.query_one("#status", widgets.Static).update("Ready to record")
            logger.info("Audio Monitor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize: {e}", exc_info=True)
            self.query_one("#status", widgets.Static).update(f"Init error: {e}")

    def update_device_list(self):
        """Update the device list in the UI."""
        logger.info("Updating device list")
        device_select = self.query_one("#device-select", widgets.Select)
        devices = self.device_manager.refresh_devices()
        logger.info(f"Found {len(devices)} audio devices")
        for dev in devices:
            logger.debug(f"  Device {dev['id']}: {dev.get('name', 'Unknown')}")
        device_select.set_options(
            [
                (str(dev.get("name", f"Device {dev['id']}")), str(dev["id"]))
                for dev in devices
            ]
        )

    def watch_is_recording(self, recording: bool):
        """React to recording state changes."""
        try:
            record_btn = self.query_one("#record-btn", widgets.Button)
            stop_btn = self.query_one("#stop-btn", widgets.Button)
            status = self.query_one("#status", widgets.Static)

            if recording:
                record_btn.disabled = True
                stop_btn.disabled = False
                status.update("Recording...")
            else:
                record_btn.disabled = False
                stop_btn.disabled = True
                status.update("Stopped")
        except Exception:
            # UI elements may not be available during shutdown
            pass

    def watch_audio_data(self, data: Optional[np.ndarray]):
        """Update waveform when audio data changes."""
        if data is not None and len(data) > 0:
            waveform = self.query_one("#waveform", WaveformWidget)
            sample_rate = int(self.query_one("#sample-rate-input", widgets.Input).value)
            waveform.set_audio_data(data, sample_rate)

    def on_button_pressed(self, event: widgets.Button.Pressed):
        """Handle button press events."""
        button_id = event.button.id
        logger.info(f"Button pressed: {button_id}")

        try:
            if button_id == "record-btn":
                self.start_recording()
            elif button_id == "stop-btn":
                self.stop_recording()
            elif button_id == "playback-btn":
                # Check if audio data exists and has content
                has_data = (
                    self.audio_data is not None
                    and isinstance(self.audio_data, np.ndarray)
                    and self.audio_data.size > 0
                )
                if has_data:
                    self.play_audio()
                else:
                    msg = "No audio data to play back"
                    logger.warning(msg)
                    self.query_one("#status", widgets.Static).update(msg)
            elif button_id == "save-btn":
                # Check if audio data exists and has content
                has_data = (
                    self.audio_data is not None
                    and isinstance(self.audio_data, np.ndarray)
                    and self.audio_data.size > 0
                )
                if has_data:
                    self.save_audio()
                else:
                    msg = "No audio data to save"
                    logger.warning(msg)
                    self.query_one("#status", widgets.Static).update(msg)
            elif button_id == "clear-btn":
                self.clear_audio()
        except Exception as e:
            error_msg = f"Error handling button {button_id}: {e}"
            logger.error(error_msg, exc_info=True)
            self.query_one("#status", widgets.Static).update(error_msg)

    def action_record(self):
        """Start recording."""
        if not self.is_recording:
            self.start_recording()

    def action_toggle_record(self):
        """Toggle recording state."""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def action_playback(self):
        """Play back recorded audio."""
        if self.audio_data is not None:
            self.play_audio()

    def action_save(self):
        """Save recorded audio."""
        if self.audio_data is not None:
            self.save_audio()

    def start_recording(self):
        """Start audio recording."""
        logger.info("Starting recording")
        try:
            device_select_value = self.query_one("#device-select", widgets.Select).value
            if device_select_value is None:
                error_msg = "No audio device selected"
                logger.error(error_msg)
                self.query_one("#status", widgets.Static).update(f"Error: {error_msg}")
                return

            device_id = int(device_select_value)
            sample_rate = int(self.query_one("#sample-rate-input", widgets.Input).value)
            channels = int(self.query_one("#channels-select", widgets.Select).value)
            buffer_size = int(self.query_one("#buffer-size-input", widgets.Input).value)

            logger.info(
                f"Recording config: device={device_id}, sample_rate={sample_rate}, "
                f"channels={channels}, buffer={buffer_size}"
            )

            # Get device info to determine actual sample rate
            device_info = self.device_manager.get_device_info(device_id)
            if device_info:
                device_samplerate = int(device_info["default_samplerate"])
                logger.info(f"Device native sample rate: {device_samplerate}")
            else:
                device_samplerate = sample_rate
                logger.warning(
                    f"Could not get device info, using requested rate: {sample_rate}"
                )

            # Create temporary file for recording
            timestamp = int(time.time())
            self.current_file = self.temp_dir / f"recording_{timestamp}.wav"
            logger.info(f"Recording to file: {self.current_file}")

            self.recorder = AudioRecorder(str(self.current_file), sample_rate)
            if not self.recorder.start_recording():
                error_msg = "AudioRecorder failed to start"
                logger.error(error_msg)
                raise Exception(error_msg)

            # Initialize audio processor with same settings as wrapper
            # Use model sample rate of 16000 (standard for Vosk models)
            model_sample_rate = 16000
            self.audio_processor = AudioProcessor(
                device_rate=device_samplerate,
                model_rate=model_sample_rate,
                noise_filter_enabled=True,
                noise_reduction_strength=0.05,
                stationary_noise=False,
                silence_threshold=50.0,
                normalize_audio=False,
                normalization_target_level=0.3,
                vad_hysteresis_chunks=10,
                noise_reduction_min_rms_ratio=0.5,
                pre_roll_duration=2.0,
            )

            # Start audio stream
            self.audio_data = np.array([], dtype=np.float32)
            self.processed_audio_data = np.array([], dtype=np.float32)

            def audio_callback(indata, frames, time, status):
                if status:
                    logger.warning(f"Audio callback status: {status}")

                # Store raw audio data for playback
                if channels == 1:
                    raw_mono = indata[:, 0]
                else:
                    # Convert to mono by averaging channels
                    raw_mono = np.mean(indata, axis=1)

                self.audio_data = np.concatenate([self.audio_data, raw_mono])

                # Process audio through the same pipeline as the wrapper
                try:
                    # Convert to int16 for processing (same as wrapper)
                    raw_int16 = (raw_mono * 32767).astype(np.int16)

                    # Process through audio processor
                    processed_chunks = self.audio_processor.process_with_vad(
                        raw_int16.reshape(-1, 1)
                    )

                    # Collect processed audio
                    for processed_chunk in processed_chunks:
                        self.processed_audio_data = np.concatenate(
                            [
                                self.processed_audio_data,
                                processed_chunk.astype(np.float32) / 32767.0,
                            ]
                        )

                except Exception as e:
                    logger.error(f"Audio processing error: {e}", exc_info=True)

                # Write raw audio to recording file
                if self.recorder:
                    self.recorder.write_audio((raw_mono * 32767).astype(np.int16))

            # Use same stream settings as wrapper
            self.recording_stream = sd.InputStream(
                device=device_id,
                channels=channels,
                samplerate=device_samplerate,  # Use device's native rate
                blocksize=1024,  # Same as wrapper
                dtype="int16",  # Same as wrapper
                callback=audio_callback,
            )

            self.recording_stream.start()
            self.is_recording = True
            logger.info("Recording started successfully")

        except Exception as e:
            error_msg = f"Failed to start recording: {e}"
            logger.error(error_msg, exc_info=True)
            self.query_one("#status", widgets.Static).update(f"Error: {e}")

    def stop_recording(self):
        """Stop audio recording."""
        logger.info("Stopping recording")
        try:
            if self.recording_stream:
                self.recording_stream.stop()
                self.recording_stream.close()
                self.recording_stream = None
                logger.info("Recording stream stopped")

            if self.recorder:
                self.recorder.stop_recording()
                self.recorder = None
                logger.info("AudioRecorder stopped")

            if self.audio_processor:
                self.audio_processor.cleanup()
                self.audio_processor = None
                logger.info("AudioProcessor cleaned up")

            self.is_recording = False
            try:
                status = self.query_one("#status", widgets.Static)
                if self.current_file:
                    msg = f"Recording saved to {self.current_file.name}"
                    status.update(msg)
                    logger.info(f"Recording saved: {self.current_file}")
                else:
                    status.update("Recording stopped")
                    logger.info("Recording stopped")
            except Exception as e:
                logger.error(f"Error updating status: {e}")

        except Exception as e:
            error_msg = f"Error stopping recording: {e}"
            logger.error(error_msg, exc_info=True)
            try:
                self.query_one("#status", widgets.Static).update(f"Error stopping: {e}")
            except Exception:
                pass

    def play_audio(self):
        """Play back recorded audio."""
        logger.info("Starting audio playback")
        # Choose which audio to play: processed if available, otherwise raw
        has_processed = (
            self.processed_audio_data is not None
            and isinstance(self.processed_audio_data, np.ndarray)
            and self.processed_audio_data.size > 0
        )
        audio_to_play = self.processed_audio_data if has_processed else self.audio_data

        # Verify we have valid audio data
        if audio_to_play is None or not isinstance(audio_to_play, np.ndarray) or audio_to_play.size == 0:
            msg = "No audio data available for playback"
            logger.warning(msg)
            self.query_one("#status", widgets.Static).update(msg)
            return

        logger.info(f"Playing {len(audio_to_play)} audio samples")

        try:
            # Use model sample rate for playback (16kHz for processed audio)
            has_processed = (
                self.processed_audio_data is not None
                and isinstance(self.processed_audio_data, np.ndarray)
                and self.processed_audio_data.size > 0
            )
            sample_rate = (
                16000
                if has_processed
                else int(self.query_one("#sample-rate-input", widgets.Input).value)
            )

            def playback_callback(outdata, frames, time, status):
                if status:
                    logger.warning(f"Playback callback status: {status}")

                if hasattr(self, "_playback_pos"):
                    pos = self._playback_pos
                else:
                    pos = 0

                remaining = len(audio_to_play) - pos
                if remaining <= 0:
                    outdata.fill(0)
                    return

                to_copy = min(frames, remaining)
                outdata[:to_copy, 0] = audio_to_play[pos : pos + to_copy]
                outdata[to_copy:, 0] = 0

                self._playback_pos = pos + to_copy

            self._playback_pos = 0
            self.playback_stream = sd.OutputStream(
                samplerate=sample_rate,
                channels=1,
                callback=playback_callback,
            )
            self.playback_stream.start()

            audio_type = "processed" if self.processed_audio_data is not None else "raw"
            self.query_one("#status", widgets.Static).update(
                f"Playing back {audio_type} audio..."
            )

            # Stop playback after audio finishes
            playback_duration = len(audio_to_play) / sample_rate
            logger.info(f"Playback duration: {playback_duration:.2f}s")
            self.set_timer(playback_duration + 0.5, self.stop_playback)

        except Exception as e:
            error_msg = f"Playback error: {e}"
            logger.error(error_msg, exc_info=True)
            self.query_one("#status", widgets.Static).update(error_msg)

    def stop_playback(self):
        """Stop audio playback."""
        logger.info("Stopping playback")
        try:
            if self.playback_stream:
                self.playback_stream.stop()
                self.playback_stream.close()
                self.playback_stream = None
                logger.info("Playback stopped")

            try:
                self.query_one("#status", widgets.Static).update("Playback complete")
            except Exception:
                # UI may be shutting down
                pass

        except Exception as e:
            error_msg = f"Error stopping playback: {e}"
            logger.error(error_msg, exc_info=True)
            try:
                self.query_one("#status", widgets.Static).update(error_msg)
            except Exception:
                # UI may be shutting down
                pass

    def save_audio(self):
        """Save recorded audio to a permanent file."""
        logger.info("Saving audio")
        try:
            # Check if audio data exists and is not empty
            has_data = self.audio_data is not None and (
                isinstance(self.audio_data, np.ndarray) and self.audio_data.size > 0
            )

            if not has_data:
                msg = "No audio data to save"
                logger.warning(msg)
                self.query_one("#status", widgets.Static).update(msg)
                return

            # For now, the audio is already saved to temp file by AudioRecorder
            # In the future, we could add a file dialog to choose save location
            if self.current_file and self.current_file.exists():
                msg = f"Audio already saved to {self.current_file}"
                logger.info(msg)
                self.query_one("#status", widgets.Static).update(msg)
            else:
                msg = "No file to save (recording may not have been started properly)"
                logger.warning(msg)
                self.query_one("#status", widgets.Static).update(msg)

        except Exception as e:
            error_msg = f"Error saving audio: {e}"
            logger.error(error_msg, exc_info=True)
            self.query_one("#status", widgets.Static).update(error_msg)

    def clear_audio(self):
        """Clear recorded audio data."""
        logger.info("Clearing audio data")
        try:
            # Set to empty arrays instead of None to avoid truth value errors
            self.audio_data = np.array([], dtype=np.float32)
            self.processed_audio_data = np.array([], dtype=np.float32)
            self.current_file = None

            # Clear waveform display
            waveform = self.query_one("#waveform", WaveformWidget)
            waveform.audio_data = None
            waveform.refresh()

            msg = "Audio data cleared"
            logger.info(msg)
            self.query_one("#status", widgets.Static).update(msg)

        except Exception as e:
            error_msg = f"Error clearing audio: {e}"
            logger.error(error_msg, exc_info=True)
            self.query_one("#status", widgets.Static).update(error_msg)

    def on_unmount(self):
        """Clean up when app is closing."""
        logger.info("Audio Monitor shutting down")

        # Stop recording stream
        try:
            if self.recording_stream:
                self.recording_stream.stop()
                self.recording_stream.close()
                self.recording_stream = None
                logger.info("Recording stream stopped")
        except Exception as e:
            logger.error(f"Error stopping recording stream: {e}")

        # Stop recorder
        try:
            if self.recorder:
                self.recorder.stop_recording()
                self.recorder = None
                logger.info("AudioRecorder stopped")
        except Exception as e:
            logger.error(f"Error stopping recorder: {e}")

        # Cleanup audio processor
        try:
            if self.audio_processor:
                self.audio_processor.cleanup()
                self.audio_processor = None
                logger.info("AudioProcessor cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up audio processor: {e}")

        # Stop playback stream
        try:
            if self.playback_stream:
                self.playback_stream.stop()
                self.playback_stream.close()
                self.playback_stream = None
                logger.info("Playback stopped")
        except Exception as e:
            logger.error(f"Error stopping playback stream: {e}")

        # Clean up temp files
        try:
            import shutil

            logger.info(f"Cleaning up temporary directory: {self.temp_dir}")
            shutil.rmtree(self.temp_dir)
            logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")

        logger.info("Audio Monitor shutdown complete")


def main():
    """Main entry point for the audio monitor."""
    parser = argparse.ArgumentParser(
        description="Live audio monitoring for vosk-wrapper-1000"
    )
    parser.add_argument("--device", type=int, help="Audio device ID to use")
    parser.add_argument(
        "--sample-rate", type=int, default=16000, help="Sample rate for recording"
    )
    parser.add_argument(
        "--channels", type=int, default=1, help="Number of audio channels"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )

    args = parser.parse_args()

    # Set log level
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")

    logger.info("="*60)
    logger.info("Audio Monitor for vosk-wrapper-1000")
    logger.info("="*60)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Command line args: {args}")

    try:
        app = AudioMonitorApp()

        # Set initial values from command line args
        if args.device is not None:
            # This would need to be handled in the app after mounting
            logger.info(f"Device specified: {args.device}")

        logger.info("Starting TUI application...")
        app.run()
        logger.info("Application exited normally")

    except KeyboardInterrupt:
        logger.info("Application interrupted by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\nFatal error: {e}", file=sys.stderr)
        print("Check audio_monitor.log for details", file=sys.stderr)
        sys.exit(1)

    logger.info("="*60)
    logger.info("Audio Monitor session ended")
    logger.info("="*60)


if __name__ == "__main__":
    main()
