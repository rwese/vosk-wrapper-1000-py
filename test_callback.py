#!/usr/bin/env python3
"""
Test the exact callback function from main.py
"""

import time

import sounddevice as sd


# Exact callback from main.py
def audio_callback(indata, frames, time, status):
    """Audio callback for sounddevice."""
    print(
        f"CALLED: frames={frames}, shape={indata.shape}, max={indata.max():.6f}, status={status}"
    )
    return True


def main():
    print("Testing main.py callback function...")

    try:
        print("Creating stream with main.py callback...")
        stream = sd.InputStream(
            samplerate=44100,
            channels=1,
            dtype="int16",
            blocksize=1024,
            callback=audio_callback,
        )

        print("Stream created, starting...")
        stream.start()

        print("Recording for 3 seconds...")
        start_time = time.time()
        while time.time() - start_time < 3:
            time.sleep(0.1)

        print("Stopping stream...")
        stream.stop()
        stream.close()
        print("Test completed successfully!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
