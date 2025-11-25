#!/usr/bin/env python3
"""Test that the resampler initialization fix works."""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import soxr

from vosk_wrapper_1000.audio_processor import AudioProcessor
from vosk_wrapper_1000.audio_recorder import AudioRecorder


def test_resampler_initialization():
    """Test that resampler is properly initialized after rate updates."""
    print("=" * 60)
    print("Test: Resampler Initialization After Rate Update")
    print("=" * 60)

    # Simulate daemon initialization with placeholders (OLD BUG)
    print("\n1. Create AudioProcessor with placeholder rates (both 16000)...")
    audio_processor_old = AudioProcessor(
        device_rate=16000,  # Placeholder
        model_rate=16000,  # Placeholder
        noise_filter_enabled=False,
    )
    print(f"   device_rate: {audio_processor_old.device_rate}")
    print(f"   model_rate: {audio_processor_old.model_rate}")
    print(f"   soxr_resampler: {audio_processor_old.soxr_resampler}")

    # Update rates (like daemon does)
    print("\n2. Update rates to actual values...")
    audio_processor_old.device_rate = 44100
    audio_processor_old.model_rate = 16000
    print(f"   device_rate: {audio_processor_old.device_rate}")
    print(f"   model_rate: {audio_processor_old.model_rate}")
    print(f"   soxr_resampler: {audio_processor_old.soxr_resampler}")

    if audio_processor_old.soxr_resampler is None:
        print("   ✗ BUG: Resampler is still None after rate update!")
    else:
        print("   ✓ Resampler is initialized")

    # Now test with the fix
    print("\n3. Test with manual resampler initialization (FIX)...")
    if audio_processor_old.device_rate != audio_processor_old.model_rate:
        audio_processor_old.soxr_resampler = soxr.ResampleStream(
            in_rate=audio_processor_old.device_rate,
            out_rate=audio_processor_old.model_rate,
            num_channels=1,
            quality="HQ",
        )
        print(
            f"   Resampler created: {audio_processor_old.device_rate} Hz → {audio_processor_old.model_rate} Hz"
        )

    print(f"   soxr_resampler: {audio_processor_old.soxr_resampler}")

    if audio_processor_old.soxr_resampler is not None:
        print("   ✓ Resampler is now initialized!")
    else:
        print("   ✗ Resampler is still None!")

    # Test resampling
    print("\n4. Test actual resampling...")
    test_audio_44100 = np.random.randint(-1000, 1000, size=44100, dtype=np.int16)
    print(f"   Input: {len(test_audio_44100)} samples @ 44100 Hz (1 second)")

    processed = audio_processor_old.process_audio_chunk(test_audio_44100)
    print(f"   Output: {len(processed)} samples @ 16000 Hz")
    print("   Expected output: ~16000 samples")

    if 15500 < len(processed) < 16500:  # Allow some tolerance
        print("   ✓ Resampling works correctly!")
    else:
        print("   ✗ Resampling failed!")

    # Test recording
    print("\n5. Test recording with correct sample rate...")
    temp_file = tempfile.mktemp(suffix=".wav")
    audio_recorder = AudioRecorder(temp_file, audio_processor_old.model_rate)
    audio_recorder.start_recording()
    audio_recorder.write_audio(processed)
    audio_recorder.stop_recording()

    import wave

    with wave.open(temp_file, "rb") as wf:
        print(f"   WAV header sample rate: {wf.getframerate()} Hz")
        print(f"   Expected: {audio_processor_old.model_rate} Hz")
        if wf.getframerate() == audio_processor_old.model_rate:
            print("   ✓ WAV header is correct!")
        else:
            print("   ✗ WAV header mismatch!")

    Path(temp_file).unlink()

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_resampler_initialization()
