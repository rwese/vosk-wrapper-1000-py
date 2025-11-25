#!/usr/bin/env python3
"""
Test audio stream creation with device 4.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    import sounddevice as sd

    print("✓ sounddevice imported")
except ImportError as e:
    print(f"✗ Failed to import sounddevice: {e}")
    sys.exit(1)


def test_stream_creation():
    """Test creating stream with different sample rates."""
    device_id = 4

    print(f"\nTesting device {device_id} (Tiger Lake microphone)...")

    # Test with device rate (48000 Hz)
    print("\n1. Testing with device native rate (48000 Hz):")
    try:
        stream1 = sd.InputStream(
            samplerate=48000,
            device=device_id,
            channels=1,
            dtype="int16",
            blocksize=1024,
        )
        print("   ✓ Stream created at 48000 Hz")
        stream1.close()
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test with model rate (16000 Hz)
    print("\n2. Testing with model rate (16000 Hz):")
    try:
        stream2 = sd.InputStream(
            samplerate=16000,
            device=device_id,
            channels=1,
            dtype="int16",
            blocksize=1024,
        )
        print("   ✓ Stream created at 16000 Hz")
        stream2.close()
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test with default parameters (let sounddevice decide)
    print("\n3. Testing with default parameters:")
    try:
        stream3 = sd.InputStream(
            device=device_id,
            channels=1,
            dtype="int16",
            blocksize=1024,
        )
        print("   ✓ Stream created with default parameters")
        stream3.close()
    except Exception as e:
        print(f"   ✗ Failed: {e}")


if __name__ == "__main__":
    print("AUDIO STREAM CREATION TEST")
    print("=" * 50)
    test_stream_creation()
