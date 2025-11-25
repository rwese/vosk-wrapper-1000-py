#!/usr/bin/env python3
"""Diagnostic script to test sample rate and channel configuration issues."""

import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

# Test assets directory
TESTS_DIR = Path(__file__).parent
ASSETS_DIR = TESTS_DIR / "assets"


def analyze_wav_file(filepath):
    """Analyze a WAV file and print its properties."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {filepath.name}")
    print(f"{'='*60}")

    try:
        with wave.open(str(filepath), "rb") as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            nframes = wf.getnframes()
            duration = nframes / framerate

            print(
                f"  Channels:      {channels} ({'mono' if channels == 1 else 'stereo' if channels == 2 else 'multi-channel'})"
            )
            print(f"  Sample width:  {sampwidth} bytes ({sampwidth * 8}-bit)")
            print(f"  Sample rate:   {framerate} Hz")
            print(f"  Frames:        {nframes:,}")
            print(f"  Duration:      {duration:.2f} seconds")
            print(f"  File size:     {filepath.stat().st_size:,} bytes")

            # Calculate expected size
            expected_size = nframes * channels * sampwidth + 44  # +44 for WAV header
            actual_size = filepath.stat().st_size

            if abs(expected_size - actual_size) > 100:  # Allow small header variations
                print("  ⚠️  WARNING: File size mismatch!")
                print(f"      Expected: {expected_size:,} bytes")
                print(f"      Actual:   {actual_size:,} bytes")
                print(f"      Diff:     {actual_size - expected_size:,} bytes")

            # Read and analyze audio data
            wf.rewind()
            audio_bytes = wf.readframes(nframes)
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

            print("\n  Audio data analysis:")
            print(f"    Array shape:   {audio_data.shape}")
            print(f"    Array length:  {len(audio_data):,} samples")
            print(f"    Min value:     {audio_data.min()}")
            print(f"    Max value:     {audio_data.max()}")
            print(f"    Mean:          {audio_data.mean():.2f}")
            print(
                f"    RMS:           {np.sqrt(np.mean(audio_data.astype(np.float32) ** 2)):.2f}"
            )

            # Check for silence
            rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            if rms < 100:
                print("    ⚠️  WARNING: Audio appears very quiet or silent (RMS < 100)")

            # If stereo, analyze channels separately
            if channels == 2:
                left = audio_data[0::2]
                right = audio_data[1::2]
                print("\n  Stereo channel analysis:")
                print(
                    f"    Left channel RMS:  {np.sqrt(np.mean(left.astype(np.float32) ** 2)):.2f}"
                )
                print(
                    f"    Right channel RMS: {np.sqrt(np.mean(right.astype(np.float32) ** 2)):.2f}"
                )

                # Check if channels are identical (common for mono source recorded as stereo)
                if np.array_equal(left, right):
                    print("    ℹ️  Both channels are identical (mono source)")

            return {
                "channels": channels,
                "sample_width": sampwidth,
                "sample_rate": framerate,
                "duration": duration,
                "rms": rms,
            }

    except Exception as e:
        print(f"  ❌ Error analyzing file: {e}")
        return None


def check_microphone_properties():
    """Check the default microphone's properties."""
    print(f"\n{'='*60}")
    print("Default Microphone Properties")
    print(f"{'='*60}")

    try:
        # Get default input device
        device_info = sd.query_devices(kind="input")

        print(f"  Device name:           {device_info['name']}")
        print(f"  Max input channels:    {device_info['max_input_channels']}")
        print(f"  Default sample rate:   {device_info['default_samplerate']} Hz")
        print(
            f"  Host API:              {sd.query_hostapis(device_info['hostapi'])['name']}"
        )

        # Test if we can open a stream with different configurations
        print("\n  Testing stream configurations:")

        configs = [
            (1, 16000, "Mono @ 16kHz"),
            (1, 44100, "Mono @ 44.1kHz"),
            (2, 16000, "Stereo @ 16kHz"),
            (2, 44100, "Stereo @ 44.1kHz"),
        ]

        for channels, samplerate, desc in configs:
            try:
                # Try to create stream (don't start it)
                stream = sd.InputStream(
                    channels=channels,
                    samplerate=samplerate,
                    dtype="int16",
                    blocksize=1024,
                )
                stream.close()
                print(f"    ✓ {desc}")
            except Exception as e:
                print(f"    ✗ {desc}: {e}")

        return device_info

    except Exception as e:
        print(f"  ❌ Error querying microphone: {e}")
        return None


def test_record_short_sample(duration=2.0, channels=1, samplerate=16000):
    """Record a short audio sample and analyze it."""
    print(f"\n{'='*60}")
    print(f"Recording Test Sample ({channels} ch @ {samplerate} Hz)")
    print(f"{'='*60}")

    try:
        print(f"  Recording for {duration} seconds...")
        print("  (Please make some noise during recording)")

        # Record audio
        recording = sd.rec(
            int(duration * samplerate),
            samplerate=samplerate,
            channels=channels,
            dtype="int16",
        )
        sd.wait()

        print("  Recording complete!")

        # Analyze the recording
        print("\n  Recording analysis:")
        print(f"    Shape:         {recording.shape}")
        print(f"    Samples:       {len(recording):,}")
        print(f"    Min value:     {recording.min()}")
        print(f"    Max value:     {recording.max()}")

        # Calculate RMS per channel
        if channels == 1:
            rms = np.sqrt(np.mean(recording.astype(np.float32) ** 2))
            print(f"    RMS:           {rms:.2f}")
        else:
            for ch in range(channels):
                channel_data = recording[:, ch]
                rms = np.sqrt(np.mean(channel_data.astype(np.float32) ** 2))
                print(f"    Channel {ch} RMS: {rms:.2f}")

        # Save to file for manual inspection
        output_file = ASSETS_DIR / f"test_recording_{channels}ch_{samplerate}hz.wav"
        with wave.open(str(output_file), "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(samplerate)
            wf.writeframes(recording.tobytes())

        print(f"\n  Saved to: {output_file}")
        return recording

    except Exception as e:
        print(f"  ❌ Error recording: {e}")
        import traceback

        traceback.print_exc()
        return None


def compare_daemon_vs_transcribe_recordings():
    """Compare recordings made by daemon vs transcribe-file."""
    print(f"\n{'='*60}")
    print("Comparing Daemon vs Transcribe-File Recordings")
    print(f"{'='*60}")

    # Look for existing recordings
    daemon_recordings = list(ASSETS_DIR.glob("*daemon*.wav"))
    transcribe_recordings = list(ASSETS_DIR.glob("*transcribe*.wav"))

    if daemon_recordings:
        print("\n📁 Found daemon recordings:")
        for rec in daemon_recordings:
            analyze_wav_file(rec)
    else:
        print("\n  No daemon recordings found")
        print("  To create one, run:")
        print(
            "    vosk-wrapper-1000 daemon --record-audio tests/assets/daemon_recording.wav"
        )

    if transcribe_recordings:
        print("\n📁 Found transcribe-file recordings:")
        for rec in transcribe_recordings:
            analyze_wav_file(rec)


def main():
    """Run all diagnostic tests."""
    print("\n" + "=" * 60)
    print("VOSK WRAPPER SAMPLE RATE DIAGNOSTIC TOOL")
    print("=" * 60)

    # Ensure assets directory exists
    ASSETS_DIR.mkdir(exist_ok=True)

    # 1. Check microphone properties
    device_info = check_microphone_properties()

    # 2. Analyze existing test files
    test_files = list(ASSETS_DIR.glob("*.wav"))
    if test_files:
        print(f"\n{'='*60}")
        print(f"Analyzing Existing Test Files ({len(test_files)} found)")
        print(f"{'='*60}")
        for test_file in sorted(test_files):
            analyze_wav_file(test_file)

    # 3. Compare daemon vs transcribe recordings
    compare_daemon_vs_transcribe_recordings()

    # 4. Offer to record test samples
    print(f"\n{'='*60}")
    print("Interactive Tests")
    print(f"{'='*60}")

    response = input("\nWould you like to record test samples? (y/N): ").strip().lower()
    if response == "y":
        # Test mono @ 16kHz (typical Vosk config)
        test_record_short_sample(duration=3.0, channels=1, samplerate=16000)

        # Test if stereo causes issues
        if device_info and device_info["max_input_channels"] >= 2:
            response = input("\nRecord stereo test? (y/N): ").strip().lower()
            if response == "y":
                test_record_short_sample(duration=3.0, channels=2, samplerate=16000)

    print(f"\n{'='*60}")
    print("Diagnostic Complete!")
    print(f"{'='*60}")
    print("\nRecommendations:")
    print("  1. Check if daemon recordings have correct sample rate in WAV header")
    print("  2. Compare RMS levels between daemon and transcribe-file recordings")
    print("  3. Listen to recordings and check if speed/pitch is correct")
    print("  4. If daemon audio is too slow, the sample rate in WAV header")
    print("     might not match the actual sample rate of the recorded data")


if __name__ == "__main__":
    main()
