#!/usr/bin/env python3
"""
Simple test script to debug audio stream issues on macOS.
Tests each component individually to isolate the problem.
"""

import signal
import sys
import time

import numpy as np
import sounddevice as sd


def test_basic_device_detection():
    """Test 1: Basic device detection"""
    print("=== Test 1: Basic Device Detection ===")
    try:
        devices = sd.query_devices()
        print(f"Total devices found: {len(devices)}")

        input_devices = [d for d in devices if d["max_input_channels"] > 0]
        print(f"Input devices: {len(input_devices)}")

        for i, device in enumerate(input_devices):
            print(f"  {i}: {device['name']} (ID: {device.get('device', i)})")

    except Exception as e:
        print(f"ERROR in device detection: {e}")
        return False

    return len(input_devices) > 0


def test_device_info():
    """Test 2: Get detailed device info"""
    print("\n=== Test 2: Device Info ===")
    try:
        default_device = sd.default.device
        print(f"Default input device: {default_device['input']}")
        print(f"Default output device: {default_device['output']}")

        # Get info about default input device
        if default_device["input"] is not None:
            device_id = default_device["input"]
            device_info = sd.query_devices(device_id)
            print(f"Device info: {device_info}")

    except Exception as e:
        print(f"ERROR getting device info: {e}")
        return False

    return True


def test_simple_callback(indata, frames, time, status):
    """Simple callback that just reports what it receives"""
    if status:
        print(f"Status: {status}")
        return

    if frames % 100 == 0:  # Every 100 frames
        print(
            f"Callback: {frames} frames, shape={indata.shape}, max={indata.max():.6f}, min={indata.min():.6f}"
        )

    return True


def test_stream_creation():
    """Test 3: Stream creation with simple callback"""
    print("\n=== Test 3: Stream Creation ===")
    try:
        print("Attempting to create stream...")

        # Try with the same parameters as the main app
        stream = sd.InputStream(
            samplerate=44100,
            channels=1,
            dtype="int16",
            blocksize=1024,
            callback=test_simple_callback,
        )

        print("Stream object created successfully")

        # Try to start it
        print("Starting stream...")
        stream.start()
        print("Stream started successfully")

        # Let it run for a few seconds
        print("Recording for 5 seconds...")
        start_time = time.time()

        while time.time() - start_time < 5:
            time.sleep(0.1)

        print("Stopping stream...")
        stream.stop()
        stream.close()
        print("Stream stopped successfully")
        return True

    except Exception as e:
        print(f"ERROR in stream creation: {e}")
        print(f"Error type: {type(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_direct_recording():
    """Test 4: Try recording directly with sd.rec()"""
    print("\n=== Test 4: Direct Recording ===")
    try:
        print("Attempting direct recording...")
        recording = sd.rec(
            samplerate=44100,
            channels=1,
            dtype="int16",
            duration=3,
        )

        print(f"Recording completed: {len(recording)} samples")
        print(f"Audio shape: {recording.shape}")
        print(f"Max value: {recording.max():.6f}")
        print(f"Min value: {recording.min():.6f}")
        print(f"RMS: {np.sqrt(np.mean(recording**2)):.6f}")

        return True

    except Exception as e:
        print(f"ERROR in direct recording: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("Audio Stream Debug Test")
    print("=" * 50)

    # Test 1: Device detection
    if not test_basic_device_detection():
        print("\n❌ No input devices found. Exiting.")
        sys.exit(1)

    # Test 2: Device info
    if not test_device_info():
        print("\n❌ Failed to get device info. Exiting.")
        sys.exit(1)

    # Test 3: Stream creation
    if not test_stream_creation():
        print("\n❌ Stream creation failed. This is likely the main issue.")
        print("\nPossible causes:")
        print("1. Microphone permissions not granted")
        print("2. Another app is using the microphone")
        print("3. macOS security restrictions")
        print("\nTo fix permissions:")
        print("  System Preferences → Security & Privacy → Privacy → Microphone")
        print("  Enable Terminal (or this Python app)")
        sys.exit(1)

    # Test 4: Direct recording
    if not test_direct_recording():
        print("\n❌ Direct recording failed.")
        sys.exit(1)

    print("\n✅ All tests passed! Audio system is working correctly.")


if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n\nTest interrupted by user.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    main()
