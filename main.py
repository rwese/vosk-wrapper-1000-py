import argparse
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time

import sounddevice as sd
import vosk

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

def run_stop_action(stop_action_script, transcript):
    """Runs the stop action script and pipes the transcript to it."""
    if not stop_action_script:
        return

    print(f"Running stop action: {stop_action_script}", file=sys.stderr)
    try:
        process = subprocess.Popen(
            [stop_action_script],
            stdin=subprocess.PIPE,
            stdout=sys.stderr, # Forward script output to stderr to avoid messing up our stdout stream
            stderr=sys.stderr,
            text=True
        )
        process.communicate(input=transcript)
        print(f"Stop action finished with return code {process.returncode}", file=sys.stderr)
    except Exception as e:
        print(f"Error running stop action: {e}", file=sys.stderr)

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
    parser.add_argument("--stop-action", type=str, default=None, help="Path to script to run on stop")
    parser.add_argument("--list-devices", action="store_true", help="List available audio input devices")
    args = parser.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        sys.exit(0)

    if not os.path.exists(args.model):
        print(f"Model not found at '{args.model}'. Please run download_model.py or specify correct path.", file=sys.stderr)
        sys.exit(1)

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

    # Start Audio Stream
    with sd.RawInputStream(samplerate=args.samplerate, blocksize=8000, device=device_id, dtype='int16',
                           channels=1, callback=audio_callback):
        
        was_listening = False

        while running:
            # State transition: Listening -> Not Listening
            if was_listening and not listening:
                # We just stopped. Process the accumulated transcript.
                full_transcript = "\n".join(transcript_buffer)
                if full_transcript:
                    run_stop_action(args.stop_action, full_transcript)
                transcript_buffer = [] # Clear buffer
                rec.Reset() # Reset recognizer for next session
            
            was_listening = listening

            if listening:
                try:
                    data = audio_queue.get(timeout=0.1)
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "")
                        if text:
                            print(text) # Stream to stdout
                            sys.stdout.flush()
                            transcript_buffer.append(text)
                    else:
                        # Partial results can be printed if desired, but user asked to "stream output"
                        # usually implies final results. We can uncomment below for partials.
                        # partial = json.loads(rec.PartialResult())
                        # print(partial)
                        pass
                except queue.Empty:
                    pass
            else:
                # Sleep briefly to avoid busy loop when not listening
                time.sleep(0.1)
                # Drain queue to avoid stale audio when we start again? 
                # Or keep it? Let's drain it to be clean.
                while not audio_queue.empty():
                    audio_queue.get()

    print("Exiting...", file=sys.stderr)

if __name__ == "__main__":
    main()
