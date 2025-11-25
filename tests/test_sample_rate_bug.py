#!/usr/bin/env python3
"""Test to reproduce the sample rate mismatch bug."""

import sys
import tempfile
import time
import wave
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import sounddevice as sd

from vosk_core.audio_processor import AudioProcessor
from vosk_wrapper_1000.audio_recorder import AudioRecorder
from vosk_core.model_manager import ModelManager


def test_sample_rate_flow():
    """Test the exact flow that the daemon uses for audio recording."""
    print("=" * 60)
    print("Testing Daemon Audio Recording Flow")
    print("=" * 60)

    # Simulate daemon's initialization (lines 294-296)
    temp_file = tempfile.mktemp(suffix=".wav")
    print("\n1. Creating AudioRecorder with placeholder rate...")
    audio_recorder = AudioRecorder(temp_file, 16000)  # Placeholder
    print(f"   AudioRecorder.sample_rate = {audio_recorder.sample_rate} Hz")

    # Simulate getting model sample rate (line 350)
    print("\n2. Getting model sample rate...")
    mm = ModelManager()
    model_path = mm.resolve_model_path("vosk-model-en-gb-0.1")
    model_sample_rate = mm.get_model_sample_rate(str(model_path))
    print(f"   model_sample_rate = {model_sample_rate} Hz")

    # Simulate the update (line 359)
    print("\n3. Updating AudioRecorder.sample_rate...")
    audio_recorder.sample_rate = model_sample_rate
    print(f"   AudioRecorder.sample_rate = {audio_recorder.sample_rate} Hz")

    # Start recording (line 360)
    print("\n4. Starting recording...")
    if not audio_recorder.start_recording():
        print("   ERROR: Failed to start recording!")
        return
    print("   Recording started successfully")

    # Check what was actually written to the WAV header
    import wave

    print("\n5. Checking WAV file header...")
    print("   (Note: File is still open for writing)")

    # Write some dummy audio data
    print("\n6. Writing test audio data...")
    test_audio = np.random.randint(-1000, 1000, size=8000, dtype=np.int16)
    audio_recorder.write_audio(test_audio)
    print(f"   Wrote {len(test_audio)} samples")

    # Stop recording
    print("\n7. Stopping recording...")
    audio_recorder.stop_recording()
    print("   Recording stopped")

    # Analyze the result
    print("\n8. Analyzing result...")
    with wave.open(temp_file, "rb") as wf:
        print(f"   WAV Header Sample Rate: {wf.getframerate()} Hz")
        print(f"   Expected Sample Rate:   {model_sample_rate} Hz")
        print(f"   Channels:               {wf.getnchannels()}")
        print(f"   Sample Width:           {wf.getsampwidth()} bytes")
        print(f"   Frames:                 {wf.getnframes()}")

        if wf.getframerate() == model_sample_rate:
            print("\n   ✓ PASS: Sample rate is correct!")
        else:
            print("\n   ✗ FAIL: Sample rate mismatch!")
            print(f"          Expected {model_sample_rate} Hz")
            print(f"          Got {wf.getframerate()} Hz")

    # Cleanup
    Path(temp_file).unlink()
    print("\n9. Cleanup complete")


def test_actual_daemon_recording():
    """Test recording with actual microphone input (like daemon does)."""
    print("\n" + "=" * 60)
    print("Testing Actual Microphone Recording (3 seconds)")
    print("=" * 60)

    # Get device and model sample rates
    device_info = sd.query_devices(kind="input")
    device_samplerate = int(device_info["default_samplerate"])

    mm = ModelManager()
    model_path = mm.resolve_model_path("vosk-model-en-gb-0.1")
    model_sample_rate = mm.get_model_sample_rate(str(model_path))

    print(f"\nDevice sample rate: {device_samplerate} Hz")
    print(f"Model sample rate:  {model_sample_rate} Hz")
    print(f"Will resample:      {device_samplerate != model_sample_rate}")

    # Create audio processor
    audio_processor = AudioProcessor(
        device_rate=device_samplerate,
        model_rate=model_sample_rate,
        noise_filter_enabled=False,
    )

    # Create audio recorder
    temp_file = tempfile.mktemp(suffix=".wav")
    audio_recorder = AudioRecorder(temp_file, 16000)  # Placeholder
    audio_recorder.sample_rate = model_sample_rate  # Update

    print(f"\nAudioRecorder.sample_rate before start: {audio_recorder.sample_rate} Hz")

    if not audio_recorder.start_recording():
        print("ERROR: Failed to start recording!")
        return

    print(f"AudioRecorder.sample_rate after start:  {audio_recorder.sample_rate} Hz")
    print("\nRecording from microphone for 3 seconds...")
    print(f"(The sample rate should be {model_sample_rate} Hz)")

    # Record audio
    recorded_chunks = []

    def callback(indata, frames, time_info, status):
        if status:
            print(f"Status: {status}")
        processed = audio_processor.process_audio_chunk(indata.copy())
        audio_recorder.write_audio(processed)
        recorded_chunks.append(len(processed))

    stream = sd.InputStream(
        samplerate=device_samplerate,
        blocksize=1024,
        device=None,
        dtype="int16",
        channels=1,
        callback=callback,
    )

    stream.start()
    time.sleep(3.0)
    stream.stop()
    stream.close()

    # Stop recording
    audio_recorder.stop_recording()
    audio_processor.cleanup()

    print("\nRecording complete!")
    print(f"Recorded {len(recorded_chunks)} chunks")
    print(f"Total processed frames: {sum(recorded_chunks)}")

    # Analyze result
    print("\nAnalyzing WAV file...")
    with wave.open(temp_file, "rb") as wf:
        header_rate = wf.getframerate()
        frames = wf.getnframes()
        duration = frames / header_rate

        print(f"  Header sample rate: {header_rate} Hz")
        print(f"  Expected rate:      {model_sample_rate} Hz")
        print(f"  Frames:             {frames}")
        print(f"  Duration:           {duration:.2f} seconds")

        if header_rate == model_sample_rate:
            print("\n  ✓ Sample rate is CORRECT!")
        else:
            print("\n  ✗ Sample rate is WRONG!")
            print("    This is the bug causing 'too slow' playback!")

    print(f"\nSaved to: {temp_file}")
    print(f"You can listen with: play {temp_file}")

    # Don't cleanup so user can listen to it
    return temp_file


if __name__ == "__main__":
    # Test 1: Just the initialization flow
    test_sample_rate_flow()

    # Test 2: Actual recording (requires user interaction)
    print("\n" + "=" * 60)
    response = input("\nTest actual microphone recording? (y/N): ").strip().lower()
    if response == "y":
        result_file = test_actual_daemon_recording()
        print(f"\n{'=' * 60}")
        print(f"Test complete! File saved to: {result_file}")
        print(f"{'=' * 60}")
