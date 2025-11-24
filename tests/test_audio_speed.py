#!/usr/bin/env python3
"""Diagnose audio speed/sample rate issues."""

import sys
import wave
from pathlib import Path

def analyze_audio_file(filepath):
    """Analyze an audio file and guess actual sample rate if there's a mismatch."""
    print(f"Analyzing: {filepath}")
    print("=" * 60)

    with wave.open(str(filepath), "rb") as wf:
        header_rate = wf.getframerate()
        channels = wf.getnchannels()
        frames = wf.getnframes()
        sampwidth = wf.getsampwidth()

        header_duration = frames / header_rate

        print(f"WAV Header Information:")
        print(f"  Sample rate: {header_rate} Hz")
        print(f"  Channels:    {channels}")
        print(f"  Sample width: {sampwidth} bytes ({sampwidth*8}-bit)")
        print(f"  Frames:      {frames:,}")
        print(f"  Duration:    {header_duration:.2f} seconds (according to header)")
        print()

        # Calculate what the actual duration would be at different sample rates
        print(f"If audio sounds wrong, the actual sample rate might be different:")
        print(f"Possible actual sample rates and their durations:")

        common_rates = [8000, 11025, 16000, 22050, 24000, 32000, 44100, 48000]
        for actual_rate in common_rates:
            actual_duration = frames / actual_rate
            speed_factor = header_rate / actual_rate
            print(f"  {actual_rate:5} Hz → {actual_duration:6.2f} sec ", end="")

            if abs(speed_factor - 1.0) < 0.01:
                print(f"(normal speed - matches header)")
            elif speed_factor > 1.0:
                print(f"(sounds {speed_factor:.2f}x TOO FAST if header is {header_rate} Hz)")
            else:
                print(f"(sounds {1/speed_factor:.2f}x TOO SLOW if header is {header_rate} Hz)")

        print()
        print(f"Common scenarios:")
        print(f"  - Audio sounds TOO SLOW → actual rate is LOWER than header rate")
        print(f"  - Audio sounds TOO FAST → actual rate is HIGHER than header rate")
        print()

        # Specific checks for common mismatches
        if header_rate == 16000:
            print(f"Your header says 16000 Hz. If audio sounds too slow:")
            print(f"  → Actual data might be at 8000 Hz (would sound 2x too slow)")
            print(f"  → Duration would actually be: {frames/8000:.2f} seconds")
        elif header_rate == 8000:
            print(f"Your header says 8000 Hz. If audio sounds too fast:")
            print(f"  → Actual data might be at 16000 Hz (would sound 2x too fast)")
            print(f"  → Duration would actually be: {frames/16000:.2f} seconds")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        filepath = Path(sys.argv[1])
    else:
        filepath = Path.home() / "tmp-audio.wav"

    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        print(f"Usage: {sys.argv[0]} <audio-file.wav>")
        sys.exit(1)

    analyze_audio_file(filepath)

    print()
    print("="*60)
    print("To test playback at different sample rates (using sox/play):")
    print(f"  play {filepath} rate 8000   # Force 8kHz")
    print(f"  play {filepath} rate 16000  # Force 16kHz")
    print(f"  play {filepath} rate 44100  # Force 44.1kHz")
