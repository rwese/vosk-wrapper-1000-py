import argparse
import json
import os
import queue
import signal
import sys
import threading
import time

# DO NOT import sounddevice here - it initializes PortAudio which breaks after fork
# import sounddevice as sd
import vosk
import numpy as np
from scipy import signal as scipy_signal
import noisereduce as nr

from hook_manager import HookManager
from xdg_paths import get_hooks_dir, get_models_dir, get_default_model_path
from pid_manager import write_pid, remove_pid, read_pid, list_instances, send_signal_to_instance

# Global state
running = True
listening = False
audio_queue = queue.Queue()
transcript_buffer = []
resampler = None
device_rate = None
model_rate = None
noise_filter_enabled = True

def signal_handler(sig, frame):
    global running, listening
    if sig == signal.SIGUSR1:
        print("Received SIGUSR1: Starting listening...", file=sys.stderr)
        listening = True
    elif sig == signal.SIGUSR2:
        print("Received SIGUSR2: Stopping listening...", file=sys.stderr)
        listening = False
    elif sig in (signal.SIGINT, signal.SIGTERM):
        print(f"Received signal {sig}: Terminating...", file=sys.stderr)
        running = False
        listening = False

def audio_callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    global device_rate, model_rate, noise_filter_enabled
    if status:
        print(status, file=sys.stderr)
        sys.stderr.flush()
    if listening:
        try:
            # Convert buffer to numpy array
            audio_data = np.frombuffer(indata, dtype=np.int16)

            # Apply noise filtering if enabled
            if noise_filter_enabled:
                # Convert to float for noise reduction
                audio_float = audio_data.astype(np.float32) / 32768.0
                # Apply stateless noise reduction (more CPU-efficient)
                audio_float = nr.reduce_noise(y=audio_float, sr=device_rate, stationary=True)
                # Convert back to int16
                audio_data = np.clip(audio_float * 32767, -32768, 32767).astype(np.int16)

            # Resample if needed
            if device_rate != model_rate:
                # Convert to float for resampling
                audio_float = audio_data.astype(np.float32) / 32768.0
                # Resample
                num_output = int(len(audio_float) * model_rate / device_rate)
                resampled = scipy_signal.resample(audio_float, num_output)
                # Convert back to int16
                audio_int16 = np.clip(resampled * 32767, -32768, 32767).astype(np.int16)
                audio_queue.put_nowait(bytes(audio_int16))
            else:
                audio_queue.put_nowait(bytes(audio_data))
        except queue.Full:
            # Drop audio frames if queue is full (prevents overflow)
            pass
        except Exception as e:
            print(f"Error in audio callback: {e}", file=sys.stderr)
            sys.stderr.flush()

def get_device_info(device_arg):
    """Resolves device argument and returns device ID and info."""
    import sounddevice as sd  # Import here, after fork

    if device_arg is None:
        device_id = None
        device_info = sd.query_devices(device_id, 'input')
    else:
        # Try as integer ID first
        try:
            device_id = int(device_arg)
            device_info = sd.query_devices(device_id, 'input')
        except (ValueError, sd.PortAudioError):
            # Try as name substring
            print(f"Searching for device with name containing: '{device_arg}'...", file=sys.stderr)
            devices = sd.query_devices()
            device_id = None
            for i, device in enumerate(devices):
                # We only care about input devices (max_input_channels > 0)
                if device['max_input_channels'] > 0 and device_arg.lower() in device['name'].lower():
                    print(f"Found device: {device['name']} (ID: {i})", file=sys.stderr)
                    device_id = i
                    device_info = device
                    break

            if device_id is None:
                print(f"Error: No input device found matching '{device_arg}'", file=sys.stderr)
                sys.exit(1)

    return device_id, device_info

def get_device_id(device_arg):
    """Resolves device argument (int or str) to a device ID."""
    device_id, _ = get_device_info(device_arg)
    return device_id

def get_model_sample_rate(model_path):
    """Extract sample rate from model's mfcc.conf file."""
    mfcc_conf = os.path.join(model_path, "conf", "mfcc.conf")
    if os.path.exists(mfcc_conf):
        try:
            with open(mfcc_conf, 'r') as f:
                for line in f:
                    if '--sample-frequency' in line:
                        # Extract: --sample-frequency=16000
                        rate = int(line.split('=')[1].strip())
                        return rate
        except (IOError, ValueError, IndexError):
            pass
    # Default to 16000 if not found
    return 16000

def run_service(args):
    """Run the main voice recognition service."""
    global running, listening, transcript_buffer, noise_filter_enabled
    aborting = False

    # Disable PulseAudio autospawn to avoid hanging in fork
    os.environ['PULSE_NO_SIMD'] = '1'
    os.environ['PULSE_LATENCY_MSEC'] = '30'

    # Set noise filter state from args
    noise_filter_enabled = not args.disable_noise_filter

    # Handle --list-devices before fork (special case)
    if args.list_devices:
        import sounddevice as sd
        devices = sd.query_devices()
        print(f"{'ID':<4} {'Name':<50} {'Channels':<10} {'Sample Rate':<12}")
        print("-" * 80)
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                channels = f"{device['max_input_channels']} in"
                samplerate = f"{int(device['default_samplerate'])} Hz"
                print(f"{i:<4} {device['name']:<50} {channels:<10} {samplerate:<12}")
        sys.exit(0)

    # Fork to background unless --foreground specified
    # IMPORTANT: Fork BEFORE initializing sounddevice/PortAudio to avoid state corruption
    if not args.foreground:
        pid = os.fork()
        if pid > 0:
            # Parent process
            print(f"Started instance '{args.name}' in background with PID {pid}")
            sys.exit(0)
        # Child process continues...

    if not os.path.exists(args.model):
        print(f"Model not found at '{args.model}'. Please run vosk-download-model-1000 or specify correct path.", file=sys.stderr)
        sys.exit(1)

    # Auto-detect model's required sample rate
    detected_model_rate = get_model_sample_rate(args.model)

    # Use detected rate if user didn't specify --samplerate explicitly
    # Check if samplerate is the default value (16000)
    if args.samplerate == 16000 and detected_model_rate != 16000:
        model_sample_rate = detected_model_rate
        print(f"Auto-detected model sample rate: {model_sample_rate} Hz", file=sys.stderr)
    else:
        model_sample_rate = args.samplerate
        if args.samplerate != detected_model_rate:
            print(f"Warning: Model expects {detected_model_rate} Hz but using {args.samplerate} Hz", file=sys.stderr)

    # Write PID file
    instance_name = args.name
    write_pid(instance_name)
    print(f"Instance '{instance_name}' starting...", file=sys.stderr)

    # Initialize HookManager
    hook_manager = HookManager(args.hooks_dir)

    # NOW it's safe to initialize PortAudio (after fork)
    # Resolve device and get info
    device_id, device_info = get_device_info(args.device)

    # Get the device's default sample rate
    device_samplerate = int(device_info['default_samplerate'])

    # Set global rates
    global device_rate, model_rate
    device_rate = device_samplerate      # Use device's native rate
    model_rate = model_sample_rate       # Model's required rate (auto-detected or specified)

    if device_rate != model_rate:
        print(f"Device sample rate: {device_rate} Hz, Model rate: {model_rate} Hz", file=sys.stderr)
        print(f"Audio will be resampled from {device_rate} Hz to {model_rate} Hz", file=sys.stderr)
    else:
        print(f"Audio sample rate: {model_rate} Hz (no resampling needed)", file=sys.stderr)

    # Log noise filter status
    if noise_filter_enabled:
        print("Noise filtering: ENABLED", file=sys.stderr)
    else:
        print("Noise filtering: DISABLED", file=sys.stderr)

    # Load Model
    print(f"Loading model from {args.model}...", file=sys.stderr)
    model = vosk.Model(args.model)

    # Create recognizer with optional grammar (use model's required rate)
    if args.grammar:
        print(f"Using grammar: {args.grammar}", file=sys.stderr)
        rec = vosk.KaldiRecognizer(model, model_rate, args.grammar)
    else:
        rec = vosk.KaldiRecognizer(model, model_rate)

    # Configure recognizer options
    if args.words:
        print("Enabling word-level timestamps", file=sys.stderr)
        rec.SetWords(True)

    if args.partial_words:
        print("Enabling partial word results", file=sys.stderr)
        rec.SetPartialWords(True)

    # Setup Signal Handlers
    signal.signal(signal.SIGUSR1, signal_handler)
    signal.signal(signal.SIGUSR2, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"Service started. PID: {os.getpid()}", file=sys.stderr)
    print(f"Using audio device: {device_info['name']} (ID: {device_id})", file=sys.stderr)
    print("Send SIGUSR1 to start listening, SIGUSR2 to stop.", file=sys.stderr)

    # Audio Stream Management
    stream = None

    try:
        while running:
            # Check if we need to start listening
            if listening and stream is None:
                print("Starting microphone stream...", file=sys.stderr)
                print(f"DEBUG: device_rate={device_rate}, device_id={device_id}", file=sys.stderr)
                sys.stderr.flush()

                try:
                    import sounddevice as sd  # Import here, in child process after fork
                    print("DEBUG: About to create RawInputStream...", file=sys.stderr)
                    sys.stderr.flush()

                    # Create stream WITHOUT auto-start to avoid blocking
                    stream = sd.RawInputStream(
                        samplerate=device_rate,
                        blocksize=8000,
                        device=device_id,
                        dtype='int16',
                        channels=1,
                        callback=audio_callback,
                        prime_output_buffers_using_stream_callback=False
                    )
                    print("DEBUG: RawInputStream object created, now starting...", file=sys.stderr)
                    sys.stderr.flush()

                    # Explicitly start the stream
                    stream.start()

                    print("DEBUG: RawInputStream started successfully!", file=sys.stderr)
                    sys.stderr.flush()
                    print(f"Microphone stream started at {device_rate} Hz.", file=sys.stderr)
                    sys.stderr.flush()

                    # Execute START hooks
                    action = hook_manager.run_hooks("start")
                    if action == 100:
                        listening = False
                    elif action == 101:
                        running = False
                        listening = False
                    elif action == 102:
                        running = False
                        listening = False
                        aborting = True

                except Exception as e:
                    print(f"Error starting stream: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc(file=sys.stderr)
                    sys.stderr.flush()
                    listening = False
                    stream = None

            # Check if we need to stop listening
            if not listening and stream is not None:
                print("Stopping microphone stream...", file=sys.stderr)
                stream.stop()
                stream.close()
                stream = None
                print("Microphone stream stopped.", file=sys.stderr)
                
                # Process accumulated transcript
                full_transcript = "\n".join(transcript_buffer)
                
                # Execute STOP hooks
                # We pass the full transcript as payload
                action = hook_manager.run_hooks("stop", payload=full_transcript)
                
                transcript_buffer = [] # Clear buffer
                rec.Reset() # Reset recognizer for next session
                
                if action == 101:
                    running = False

            if listening and stream is not None:
                try:
                    data = audio_queue.get(timeout=0.1)
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "")
                        if text:
                            print(text) # Stream to stdout
                            sys.stdout.flush()
                            transcript_buffer.append(text)
                            
                            # Execute LINE hooks
                            # Payload is full transcript (stdin), Arg is current line
                            full_context = "\n".join(transcript_buffer)
                            action = hook_manager.run_hooks("line", payload=full_context, args=[text])
                            if action == 100:
                                listening = False
                            elif action == 101:
                                running = False
                                listening = False
                            elif action == 102:
                                running = False
                                listening = False
                                aborting = True
                    else:
                        pass
                except queue.Empty:
                    pass
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

        # Ensure stop hooks are run if we exit while listening or have data
        if (listening or transcript_buffer) and running == False and not aborting:
             # We are exiting.
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
    sig = signal.SIGKILL if args.force else signal.SIGTERM
    sig_name = "SIGKILL (force kill)" if args.force else "SIGTERM (graceful)"
    if send_signal_to_instance(args.name, sig):
        print(f"Sent {sig_name} signal to instance '{args.name}'")
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
    default_model = str(get_default_model_path())
    default_hooks_dir = str(get_hooks_dir())

    parser = argparse.ArgumentParser(
        description="Vosk Speech Recognition Service - Control multiple voice recognition instances",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a daemon instance (noise filtering enabled by default)
  vosk-wrapper-1000 daemon --name my-instance

  # Disable noise filtering if needed
  vosk-wrapper-1000 daemon --disable-noise-filter

  # Control instances
  vosk-wrapper-1000 list
  vosk-wrapper-1000 start my-instance
  vosk-wrapper-1000 stop my-instance
  vosk-wrapper-1000 terminate my-instance

For more information, visit: https://github.com/rwese/vosk-wrapper-1000-py
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Daemon command (runs as background service)
    daemon_parser = subparsers.add_parser('daemon', help='Run the voice recognition service as daemon')
    daemon_parser.add_argument("--name", type=str, default="default",
                           help="Instance name for managing multiple processes (default: default)")
    daemon_parser.add_argument("--model", type=str, default=default_model,
                           help=f"Path to Vosk model directory (default: {default_model})")
    daemon_parser.add_argument("--device", type=str, default=None,
                           help="Input device ID or Name substring")
    daemon_parser.add_argument("--samplerate", type=int, default=16000,
                           help="Sample rate in Hz (default: auto-detect from model)")
    daemon_parser.add_argument("--hooks-dir", type=str, default=default_hooks_dir,
                           help=f"Path to hooks directory (default: {default_hooks_dir})")
    daemon_parser.add_argument("--list-devices", action="store_true",
                           help="List available audio input devices")
    daemon_parser.add_argument("--foreground", action="store_true",
                           help="Run in foreground (default: run as daemon in background)")

    # Vosk recognition options
    daemon_parser.add_argument("--words", action="store_true",
                           help="Enable word-level timestamps in recognition output")
    daemon_parser.add_argument("--partial-words", action="store_true",
                           help="Enable partial word results during recognition")
    daemon_parser.add_argument("--grammar", type=str, default=None,
                           help="Grammar/vocabulary to restrict recognition (space-separated words)")

    # Audio processing options
    daemon_parser.add_argument("--disable-noise-filter", action="store_true",
                           help="Disable noise filtering (enabled by default)")

    daemon_parser.set_defaults(func=run_service)

    # Start command
    start_parser = subparsers.add_parser('start', help='Start listening on a running instance')
    start_parser.add_argument("name", nargs='?', default="default",
                             help="Instance name (default: default)")
    start_parser.set_defaults(func=cmd_start)

    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop listening on a running instance')
    stop_parser.add_argument("name", nargs='?', default="default",
                            help="Instance name (default: default)")
    stop_parser.set_defaults(func=cmd_stop)

    # Terminate command
    terminate_parser = subparsers.add_parser('terminate', help='Terminate a running instance')
    terminate_parser.add_argument("name", nargs='?', default="default",
                                 help="Instance name (default: default)")
    terminate_parser.add_argument("--force", "-f", action="store_true",
                                 help="Force kill with SIGKILL instead of graceful SIGTERM")
    terminate_parser.set_defaults(func=cmd_terminate)

    # List command
    list_parser = subparsers.add_parser('list', help='List all running instances')
    list_parser.set_defaults(func=cmd_list)

    args = parser.parse_args()

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Execute the command
    args.func(args)

if __name__ == "__main__":
    main()
