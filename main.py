import argparse
import json
import os
import queue
import signal
import sys
import threading
import time

import sounddevice as sd
import vosk

from hook_manager import HookManager

# Global state
running = True
listening = False
audio_queue = queue.Queue()
transcript_buffer = []

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
    if status:
        print(status, file=sys.stderr)
    if listening:
        audio_queue.put(bytes(indata))

def get_device_id(device_arg):
    """Resolves device argument (int or str) to a device ID."""
    if device_arg is None:
        return None
    
    # Try as integer ID first
    try:
        device_id = int(device_arg)
        return device_id
    except ValueError:
        pass
    
    # Try as name substring
    print(f"Searching for device with name containing: '{device_arg}'...", file=sys.stderr)
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        # We only care about input devices (max_input_channels > 0)
        if device['max_input_channels'] > 0 and device_arg.lower() in device['name'].lower():
            print(f"Found device: {device['name']} (ID: {i})", file=sys.stderr)
            return i
            
    print(f"Error: No input device found matching '{device_arg}'", file=sys.stderr)
    sys.exit(1)

def main():
    global running, listening, transcript_buffer

    parser = argparse.ArgumentParser(description="Vosk Speech Recognition Service")
    parser.add_argument("--model", type=str, default="model", help="Path to Vosk model directory")
    parser.add_argument("--device", type=str, default=None, help="Input device ID or Name substring")
    parser.add_argument("--samplerate", type=int, default=16000, help="Sample rate")
    parser.add_argument("--hooks-dir", type=str, default="hooks", help="Path to hooks directory")
    parser.add_argument("--list-devices", action="store_true", help="List available audio input devices")
    # stop-action is deprecated/removed in favor of hooks, but we can keep arg for compatibility or remove it.
    # User didn't explicitly say to remove it, but "replace run_stop_action" implies it. 
    # Let's remove it to be clean, or ignore it. Let's remove it.
    args = parser.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        sys.exit(0)

    if not os.path.exists(args.model):
        print(f"Model not found at '{args.model}'. Please run download_model.py or specify correct path.", file=sys.stderr)
        sys.exit(1)

    # Initialize HookManager
    hook_manager = HookManager(args.hooks_dir)

    # Resolve device
    device_id = get_device_id(args.device)

    # Load Model
    print(f"Loading model from {args.model}...", file=sys.stderr)
    model = vosk.Model(args.model)
    rec = vosk.KaldiRecognizer(model, args.samplerate)

    # Setup Signal Handlers
    signal.signal(signal.SIGUSR1, signal_handler)
    signal.signal(signal.SIGUSR2, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"Service started. PID: {os.getpid()}", file=sys.stderr)
    if device_id is not None:
        print(f"Using device ID: {device_id}", file=sys.stderr)
    print("Send SIGUSR1 to start listening, SIGUSR2 to stop.", file=sys.stderr)

    # Audio Stream Management
    stream = None

    try:
        while running:
            # Check if we need to start listening
            if listening and stream is None:
                print("Starting microphone stream...", file=sys.stderr)
                try:
                    stream = sd.RawInputStream(samplerate=args.samplerate, blocksize=8000, device=device_id, dtype='int16',
                                            channels=1, callback=audio_callback)
                    stream.start()
                    print("Microphone stream started.", file=sys.stderr)
                    
                    # Execute START hooks
                    action = hook_manager.run_hooks("start")
                    if action == 100:
                        listening = False
                    elif action == 101:
                        running = False
                        listening = False

                except Exception as e:
                    print(f"Error starting stream: {e}", file=sys.stderr)
                    listening = False # Abort listening if stream fails

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
                            action = hook_manager.run_hooks("line", payload=text)
                            if action == 100:
                                listening = False
                            elif action == 101:
                                running = False
                                listening = False
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
        print("DEBUG: Entering finally block", file=sys.stderr)
        if stream is not None:
            print("DEBUG: Stopping stream...", file=sys.stderr)
            stream.stop()
            stream.close()
            print("DEBUG: Stream stopped.", file=sys.stderr)
            
        # Ensure stop hooks are run if we exit while listening or have data
        if (listening or transcript_buffer) and running == False: 
             # We are exiting.
             full_transcript = "\n".join(transcript_buffer)
             print("Running final stop hooks...", file=sys.stderr)
             hook_manager.run_hooks("stop", payload=full_transcript)
             print("DEBUG: Final stop hooks finished.", file=sys.stderr)
    
    print("Exiting...", file=sys.stderr)

    print("Exiting...", file=sys.stderr)

if __name__ == "__main__":
    main()
