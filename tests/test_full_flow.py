#!/usr/bin/env python3
"""Test full flow like main.py."""

import signal
import sys
import time
import sounddevice as sd
import vosk
import os

sys.path.insert(0, "src")
from vosk_simple.model_manager import ModelManager


def main():
    print("1. Loading Vosk model...")
    sys.stdout.flush()
    model_path = ModelManager().default_model
    if not os.path.exists(model_path):
        print(f"✗ Model not found at {model_path}")
        sys.exit(1)
    _model = vosk.Model(str(model_path))
    print("✓ Model loaded")

    print("2. Setting up signal handlers...")
    listening = False

    def signal_handler(sig, frame):
        nonlocal listening
        print(f"Got signal {sig}")
        if sig == signal.SIGUSR1:
            listening = True

    signal.signal(signal.SIGUSR1, signal_handler)
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    print("✓ Signal handlers installed")

    print(f"3. My PID: {os.getpid()}")
    print("4. Waiting for SIGUSR1 signal...")
    sys.stdout.flush()

    while not listening:
        time.sleep(0.1)

    print("5. Signal received, creating stream...")
    sys.stdout.flush()

    try:
        stream = sd.RawInputStream(
            samplerate=48000,
            blocksize=8000,
            device=sd.default.device[0],
            dtype="int16",
            channels=1,
            callback=lambda *args: None,
        )
        print("✓ Stream created!")
        stream.start()
        print("✓ Stream started!")
        time.sleep(2)
        stream.stop()
        stream.close()
        print("✓ Test passed!")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
