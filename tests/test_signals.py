#!/usr/bin/env python3
"""Test if signal handlers block sounddevice."""

import signal
import sys
import time

import sounddevice as sd


def main():
    print("Setting up signal handlers...")

    def signal_handler(sig, frame):
        print(f"Got signal {sig}")

    signal.signal(signal.SIGUSR1, signal_handler)
    signal.signal(signal.SIGUSR2, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("Signal handlers installed")
    print("Creating stream...")
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
        print("✓ Stream created successfully!")
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
