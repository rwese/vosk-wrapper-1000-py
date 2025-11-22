#!/usr/bin/env python3
"""
Quick test to identify the audio callback issue in main.py
"""

import os
import signal
import sys
import time

import sounddevice as sd

# Module-level variable for signal manager (so callback can access it)
signal_manager: "TestSignalManager"


# Simple signal manager for testing
class TestSignalManager:
    def __init__(self):
        self.running = True
        self.listening = False

    def is_running(self):
        return self.running

    def is_listening(self):
        return self.listening

    def _handle_start(self, sig, frame):
        print("Received SIGUSR1: Starting listening...")
        self.listening = True

    def _handle_stop(self, sig, frame):
        print("Received SIGUSR2: Stopping listening...")
        self.listening = False

    def _handle_terminate(self, sig, frame):
        print(f"Received signal {sig}: Terminating...")
        self.running = False
        self.listening = False


# Test the exact callback function from main.py
def audio_callback(indata, frames, time, status):
    """Audio callback for sounddevice."""
    if status:
        print(f"Status: {status}", file=sys.stderr)
        sys.stderr.flush()

    # Check signal manager state
    listening_state = signal_manager.is_listening()
    if frames % 100 == 0:
        print(
            f"CALLBACK: frames={frames}, listening={listening_state}, max={indata.max():.6f}",
            file=sys.stderr,
        )

    if listening_state:
        try:
            # Process audio (simple pass-through for test)
            _ = indata  # No processing for this test
            return True
        except Exception as e:
            print(f"ERROR in callback: {e}", file=sys.stderr)
            return False
    else:
        if frames % 100 == 0:
            print(
                f"DROPPING: frames={frames}, listening={listening_state}",
                file=sys.stderr,
            )
        return False


def main():
    print("🔍 QUICK AUDIO CALLBACK TEST")
    print("=" * 50)

    # Setup signal manager (global so callback can access it)
    global signal_manager
    signal_manager = TestSignalManager()

    # Setup signal handlers
    def test_signal_handler(sig, frame):
        print(f"📡 Received {sig}")
        if sig == signal.SIGUSR1:
            signal_manager._handle_start(sig, frame)
        elif sig == signal.SIGUSR2:
            signal_manager._handle_stop(sig, frame)
        elif sig == signal.SIGTERM:
            signal_manager._handle_terminate(sig, frame)

    signal.signal(signal.SIGUSR1, test_signal_handler)
    signal.signal(signal.SIGUSR2, test_signal_handler)
    signal.signal(signal.SIGTERM, test_signal_handler)

    try:
        print("Creating audio stream...")

        # Create stream exactly like main.py
        stream = sd.InputStream(
            samplerate=44100,
            blocksize=1024,
            device=1,  # MacBook Pro Microphone
            dtype="int16",
            channels=1,
            callback=audio_callback,
        )

        print("✅ Stream created successfully")
        print("Starting stream...")
        stream.start()
        print("✅ Stream started")

        # Test signals
        print("Sending SIGUSR1...")
        os.kill(os.getpid(), signal.SIGUSR1)
        time.sleep(1)

        if signal_manager.is_listening():
            print("✅ Signal manager shows listening=True")
        else:
            print("❌ Signal manager shows listening=False")

        # Monitor callback for 3 seconds
        callback_count = 0
        start_time = time.time()
        while time.time() - start_time < 3:
            time.sleep(0.1)
            if signal_manager.is_listening():
                callback_count += 1
                if callback_count % 10 == 0:
                    print(f"   🎧 Callback called {callback_count} times")

        if callback_count > 0:
            print(f"✅ SUCCESS: Callback was called {callback_count} times")
        else:
            print("❌ FAILURE: Callback was never called")

        # Cleanup
        print("Stopping stream...")
        stream.stop()
        stream.close()
        print("✅ Test completed!")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
