"""Main daemon service for vosk-wrapper-1000."""

import argparse
import json
import os
import queue
import signal
import sys
import time

# Import local modules
from .audio_processor import AudioProcessor
from .audio_recorder import AudioRecorder
from .audio_system import print_audio_system_info
from .device_manager import DeviceManager
from .hook_manager import HookManager
from .model_manager import ModelManager
from .pid_manager import list_instances, remove_pid, send_signal_to_instance, write_pid
from .signal_manager import SignalManager
from .xdg_paths import get_hooks_dir


def run_service(args):
    """Run the main voice recognition service."""
    # Initialize managers
    signal_manager = SignalManager()
    model_manager = ModelManager()
    device_manager = DeviceManager()
    hook_manager = HookManager(args.hooks_dir)

    # Initialize audio components with placeholder rates
    audio_processor = AudioProcessor(
        device_rate=16000,  # Placeholder, will be updated after device detection
        model_rate=16000,  # Placeholder, will be updated after model loading
        noise_filter_enabled=not args.disable_noise_filter,
        noise_reduction_strength=args.noise_reduction,
        stationary_noise=args.stationary_noise and not args.non_stationary_noise,
    )

    audio_recorder = AudioRecorder(
        args.record_audio, 16000
    )  # Sample rate will be updated later

    # Handle --list-devices before fork (special case)
    if args.list_devices:
        device_manager.print_device_list()
        sys.exit(0)

    # Print audio system information
    print_audio_system_info()

    # Check if any audio devices are available
    available_devices = device_manager.refresh_devices()
    if not available_devices:
        print("Error: No audio input devices found on this system!", file=sys.stderr)
        print("Please check:", file=sys.stderr)
        print("  1. Microphone is connected and not muted", file=sys.stderr)
        print(
            "  2. Microphone permissions are granted to Terminal/Python",
            file=sys.stderr,
        )
        print("  3. No other application is using the microphone", file=sys.stderr)
        print("\nTo grant microphone permissions on macOS:", file=sys.stderr)
        print(
            "  System Preferences → Security & Privacy → Privacy → Microphone",
            file=sys.stderr,
        )
        print("  Enable Terminal (or your terminal application)", file=sys.stderr)
        sys.exit(1)

    # Resolve device and get info
    device_info = device_manager.get_device_info(args.device)
    if device_info is None:
        device_id = None
        device_samplerate = None
    else:
        device_id = device_info["id"]
        device_samplerate = int(device_info["default_samplerate"])

    # Validate device compatibility (only if device is specified)
    if device_id is not None:
        is_compatible, compatibility_msg = device_manager.validate_device_for_model(
            device_id, model_manager.get_model_sample_rate(args.model)
        )
        if not is_compatible:
            print(f"Error: {compatibility_msg}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Device compatibility: {compatibility_msg}", file=sys.stderr)
    else:
        print("Using default audio device", file=sys.stderr)

    # Get model sample rate
    model_sample_rate = model_manager.get_model_sample_rate(args.model)

    # Update audio processor with rates
    if device_samplerate is not None:
        audio_processor.device_rate = device_samplerate
    audio_processor.model_rate = model_sample_rate

    # Setup audio recorder with model rate
    if args.record_audio:
        audio_recorder.sample_rate = model_sample_rate
        if not audio_recorder.start_recording():
            print(f"Error opening recording file {args.record_audio}", file=sys.stderr)
            sys.exit(1)
        print(f"Recording processed audio to: {args.record_audio}", file=sys.stderr)

    # Write PID file
    instance_name = args.name
    write_pid(instance_name)
    print(f"Instance '{instance_name}' starting...", file=sys.stderr)

    # Load Model
    print(f"Loading model from {args.model}...", file=sys.stderr)
    import vosk

    model = vosk.Model(str(args.model))

    # Create recognizer with optional grammar
    if args.grammar:
        print(f"Using grammar: {args.grammar}", file=sys.stderr)
        rec = vosk.KaldiRecognizer(model, model_sample_rate, args.grammar)
    else:
        rec = vosk.KaldiRecognizer(model, model_sample_rate)

    # Configure recognizer options
    if args.words:
        print("Enabling word-level timestamps", file=sys.stderr)
        rec.SetWords(True)

    if args.partial_words:
        print("Enabling partial word results", file=sys.stderr)
        rec.SetPartialWords(True)

    # Setup signal handlers
    signal_manager._setup_handlers()

    print(f"Service started. PID: {os.getpid()}", file=sys.stderr)
    if device_info is not None:
        print(
            f"Using audio device: {device_info['name']} (ID: {device_id})",
            file=sys.stderr,
        )
    else:
        print("Using default audio device", file=sys.stderr)
    print("Send SIGUSR1 to start listening, SIGUSR2 to stop.", file=sys.stderr)

    # Audio Stream Management
    stream = None
    audio_queue = queue.Queue()
    transcript_buffer = []

    def audio_callback(indata, frames, time, status):
        """Audio callback for sounddevice."""
        if status:
            print(status, file=sys.stderr)
            sys.stderr.flush()

        if signal_manager.is_listening():
            try:
                # Process audio through our pipeline
                processed_audio = audio_processor.process_audio_chunk(indata)

                # Save to recording file if enabled
                if args.record_audio:
                    audio_recorder.write_audio(processed_audio)

                # Queue for Vosk processing
                audio_queue.put_nowait(bytes(processed_audio))
            except queue.Full:
                # Drop audio frames if queue is full (prevents overflow)
                pass
            except Exception as e:
                print(f"Error in audio callback: {e}", file=sys.stderr)
                sys.stderr.flush()

    try:
        while signal_manager.is_running():
            # Check if we need to start listening
            if signal_manager.is_listening() and stream is None:
                print("Starting microphone stream...", file=sys.stderr)
                print(
                    f"DEBUG: device_rate={audio_processor.device_rate}, device_id={device_id}",
                    file=sys.stderr,
                )
                sys.stderr.flush()

                try:
                    import sounddevice as sd  # Import here, in child process after fork

                    # Create stream using soxr-optimized callback
                    stream = sd.InputStream(
                        samplerate=audio_processor.device_rate,
                        blocksize=1024,  # Smaller blocksize for better streaming
                        device=device_id,
                        dtype="float32",  # Use float32 for better soxr integration
                        channels=1,
                        callback=audio_callback,
                    )
                    print(
                        f"Microphone stream started at {audio_processor.device_rate} Hz (using soxr resampling to {audio_processor.model_rate} Hz).",
                        file=sys.stderr,
                    )
                    sys.stderr.flush()

                    # Execute START hooks
                    action = hook_manager.run_hooks("start")
                    if action == 100:
                        signal_manager.set_listening(False)
                    elif action == 101:
                        signal_manager.set_running(False)
                        signal_manager.set_listening(False)
                    elif action == 102:
                        signal_manager.set_running(False)
                        signal_manager.set_listening(False)

                except Exception as e:
                    print(f"Error starting stream: {e}", file=sys.stderr)
                    import traceback

                    traceback.print_exc(file=sys.stderr)
                    sys.stderr.flush()
                    signal_manager.set_listening(False)

            # Check if we need to stop listening
            if not signal_manager.is_listening() and stream is not None:
                print("Stopping microphone stream...", file=sys.stderr)
                stream.stop()
                stream.close()
                stream = None
                print("Microphone stream stopped.", file=sys.stderr)

                # Process accumulated transcript
                full_transcript = "\n".join(transcript_buffer)

                # Execute STOP hooks
                action = hook_manager.run_hooks("stop", payload=full_transcript)

                transcript_buffer = []  # Clear buffer
                rec.Reset()  # Reset recognizer for next session

                if action == 101:
                    signal_manager.set_running(False)
                elif action == 102:
                    signal_manager.set_running(False)
                    signal_manager.set_listening(False)

            # Process audio if listening
            if signal_manager.is_listening() and stream is not None:
                try:
                    data = audio_queue.get(timeout=0.1)
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "")
                        if text:
                            print(text)  # Stream to stdout
                            sys.stdout.flush()
                            transcript_buffer.append(text)

                            # Execute LINE hooks
                            full_context = "\n".join(transcript_buffer)
                            action = hook_manager.run_hooks(
                                "line", payload=full_context, args=[text]
                            )
                            if action == 100:
                                signal_manager.set_listening(False)
                            elif action == 101:
                                signal_manager.set_running(False)
                                signal_manager.set_listening(False)
                            elif action == 102:
                                signal_manager.set_running(False)
                                signal_manager.set_listening(False)
                    else:
                        pass
                except queue.Empty:
                    pass
                except Exception as e:
                    print(f"Error processing audio: {e}", file=sys.stderr)
                    sys.stderr.flush()
            else:
                # Sleep briefly to avoid busy loop when not listening
                time.sleep(0.1)
                # Drain queue to avoid stale audio when we start again
                while not audio_queue.empty():
                    audio_queue.get()

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
    finally:
        if stream is not None:
            stream.stop()
            stream.close()

        # Stop recording and clean up
        if args.record_audio:
            audio_recorder.stop_recording()

        # Finalize audio processing
        audio_processor.cleanup()

        # Ensure stop hooks are run if we exit while listening or have data
        if (
            signal_manager.is_listening() or transcript_buffer
        ) and not signal_manager.is_running():
            full_transcript = "\n".join(transcript_buffer)
            print("Running final stop hooks...", file=sys.stderr)
            hook_manager.run_hooks("stop", payload=full_transcript)

        # Clean up PID file
        remove_pid(instance_name)

    print("Exiting...", file=sys.stderr)


def cmd_start(args):
    """Start listening on a named instance."""
    if send_signal_to_instance(args.name, signal.SIGUSR1):
        print(f"Sent start signal to instance '{args.name}'")
    else:
        sys.exit(1)


def cmd_stop(args):
    """Stop listening on a named instance."""
    if send_signal_to_instance(args.name, signal.SIGUSR2):
        print(f"Sent stop signal to instance '{args.name}'")
    else:
        sys.exit(1)


def cmd_terminate(args):
    """Terminate a named instance."""
    if send_signal_to_instance(args.name, signal.SIGTERM):
        print(f"Sent terminate signal to instance '{args.name}'")
    else:
        sys.exit(1)


def cmd_list(args):
    """List all running instances."""
    instances = list_instances()
    if not instances:
        print("No running instances found")
        return

    print(f"{'Name':<20} {'PID':<10}")
    print("-" * 30)
    for name, pid in instances:
        print(f"{name:<20} {pid:<10}")


def main():
    # Get XDG default paths
    default_model = ModelManager().default_model
    default_hooks_dir = get_hooks_dir()

    parser = argparse.ArgumentParser(
        description="Vosk Speech Recognition Service - Control multiple voice recognition instances",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 Examples:
  # Run a daemon instance (noise filtering enabled by default)
  vosk-wrapper-1000 daemon --name my-instance

  # Configure noise filtering
  vosk-wrapper-1000 daemon --noise-reduction 0.3 --non-stationary-noise

  # Record processed audio for review
  vosk-wrapper-1000 daemon --record-audio output.wav

  # Control instances
  vosk-wrapper-1000 list
  vosk-wrapper-1000 start my-instance
  vosk-wrapper-1000 stop my-instance
  vosk-wrapper-1000 terminate my-instance

For more information, visit: https://github.com/rwese/vosk-wrapper-1000-py
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Daemon command (runs as background service)
    daemon_parser = subparsers.add_parser(
        "daemon", help="Run voice recognition service as daemon"
    )
    daemon_parser.add_argument(
        "--name",
        type=str,
        default="default",
        help="Instance name for managing multiple processes (default: default)",
    )
    daemon_parser.add_argument(
        "--model",
        type=str,
        default=default_model,
        help=f"Path to Vosk model directory (default: {default_model})",
    )
    daemon_parser.add_argument(
        "--device", type=str, default=None, help="Input device ID or Name substring"
    )
    daemon_parser.add_argument(
        "--samplerate",
        type=int,
        default=16000,
        help="Sample rate in Hz (default: auto-detect from model)",
    )
    daemon_parser.add_argument(
        "--hooks-dir",
        type=str,
        default=default_hooks_dir,
        help=f"Path to hooks directory (default: {default_hooks_dir})",
    )
    daemon_parser.add_argument(
        "--list-devices", action="store_true", help="List available audio input devices"
    )
    daemon_parser.add_argument(
        "--foreground",
        action="store_true",
        help="Run in foreground (default: run as daemon in background)",
    )

    # Vosk recognition options
    daemon_parser.add_argument(
        "--words",
        action="store_true",
        help="Enable word-level timestamps in recognition output",
    )
    daemon_parser.add_argument(
        "--partial-words",
        action="store_true",
        help="Enable partial word results during recognition",
    )
    daemon_parser.add_argument(
        "--grammar",
        type=str,
        default=None,
        help="Grammar/vocabulary to restrict recognition (space-separated words)",
    )

    # Audio processing options
    daemon_parser.add_argument(
        "--disable-noise-filter",
        action="store_true",
        help="Disable noise filtering (enabled by default)",
    )
    daemon_parser.add_argument(
        "--noise-reduction",
        type=float,
        default=0.2,
        help="Noise reduction strength (0.0-1.0, default: 0.2)",
    )
    daemon_parser.add_argument(
        "--stationary-noise",
        action="store_true",
        default=True,
        help="Use stationary noise reduction (faster, default: True)",
    )
    daemon_parser.add_argument(
        "--non-stationary-noise",
        action="store_true",
        help="Use non-stationary noise reduction (slower but more adaptive)",
    )
    daemon_parser.add_argument(
        "--record-audio",
        type=str,
        help="Record processed audio to WAV file for review",
    )

    # Control commands
    start_parser = subparsers.add_parser(
        "start", help="Start listening on a running instance"
    )
    start_parser.add_argument(
        "name", nargs="?", default="default", help="Instance name"
    )

    stop_parser = subparsers.add_parser(
        "stop", help="Stop listening on a running instance"
    )
    stop_parser.add_argument("name", nargs="?", default="default", help="Instance name")

    terminate_parser = subparsers.add_parser(
        "terminate", help="Terminate a running instance"
    )
    terminate_parser.add_argument(
        "name", nargs="?", default="default", help="Instance name"
    )

    subparsers.add_parser("list", help="List all running instances")

    args = parser.parse_args()

    if args.command == "daemon":
        run_service(args)
    elif args.command == "start":
        cmd_start(args)
    elif args.command == "stop":
        cmd_stop(args)
    elif args.command == "terminate":
        cmd_terminate(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
