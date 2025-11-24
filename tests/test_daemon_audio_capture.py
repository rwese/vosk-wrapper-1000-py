#!/usr/bin/env python3
"""Test what the daemon actually captures from the microphone."""

import sys
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

# Test assets directory
TESTS_DIR = Path(__file__).parent
ASSETS_DIR = TESTS_DIR / "assets"
ASSETS_DIR.mkdir(exist_ok=True)


def test_daemon_style_capture(duration=3.0):
    """Simulate exactly how the daemon captures audio."""
    print("Testing daemon-style audio capture...")
    print(f"Duration: {duration} seconds")
    print("\nThis simulates the daemon's audio stream configuration:")

    # Get device info (same as daemon does)
    device_info = sd.query_devices(kind='input')
    device_samplerate = int(device_info["default_samplerate"])

    print(f"  Device: {device_info['name']}")
    print(f"  Device sample rate: {device_samplerate} Hz")
    print(f"  Max input channels: {device_info['max_input_channels']}")

    # Model sample rate (for this test model)
    model_sample_rate = 8000
    print(f"  Model sample rate: {model_sample_rate} Hz")

    # Create files to save both raw and processed audio
    raw_file = ASSETS_DIR / f"daemon_test_raw_{device_samplerate}hz.wav"
    processed_file = ASSETS_DIR / f"daemon_test_processed_{model_sample_rate}hz.wav"

    # Setup WAV files
    raw_wav = wave.open(str(raw_file), "wb")
    raw_wav.setnchannels(1)
    raw_wav.setsampwidth(2)
    raw_wav.setframerate(device_samplerate)

    processed_wav = wave.open(str(processed_file), "wb")
    processed_wav.setnchannels(1)
    processed_wav.setsampwidth(2)
    processed_wav.setframerate(model_sample_rate)

    # Import audio processor
    from vosk_wrapper_1000.audio_processor import AudioProcessor

    audio_processor = AudioProcessor(
        device_rate=device_samplerate,
        model_rate=model_sample_rate,
        noise_filter_enabled=False,  # Disable for testing
        channels=1,  # Explicitly mono
    )

    print(f"\nAudioProcessor config:")
    print(f"  device_rate: {audio_processor.device_rate}")
    print(f"  model_rate: {audio_processor.model_rate}")
    print(f"  channels: {audio_processor.channels}")
    print(f"  Will resample: {audio_processor.device_rate != audio_processor.model_rate}")

    chunk_count = [0]
    total_raw_frames = [0]
    total_processed_frames = [0]

    def audio_callback(indata, frames, callback_time, status):
        """Exactly like the daemon's callback."""
        if status:
            print(f"Status: {status}", file=sys.stderr)

        try:
            # Save raw audio (what microphone gives us)
            raw_wav.writeframes(indata.tobytes())
            total_raw_frames[0] += frames

            # Process audio (noise filtering + resampling)
            processed_audio = audio_processor.process_audio_chunk(indata.copy())

            # Save processed audio (what goes to Vosk)
            processed_wav.writeframes(processed_audio.tobytes())
            total_processed_frames[0] += len(processed_audio)

            chunk_count[0] += 1
            if chunk_count[0] % 20 == 0:
                print(f"  Chunk {chunk_count[0]}: raw={frames} frames, processed={len(processed_audio)} frames", end='\r')

        except Exception as e:
            print(f"\nError in callback: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

    print(f"\nRecording (please speak into microphone)...")
    print(f"Recording will stop automatically after {duration} seconds\n")

    # Create stream EXACTLY like daemon does
    stream = sd.InputStream(
        samplerate=device_samplerate,
        blocksize=1024,
        device=None,  # Default device
        dtype="int16",
        channels=1,  # MONO
        callback=audio_callback,
    )

    stream.start()
    time.sleep(duration)
    stream.stop()
    stream.close()

    # Cleanup
    audio_processor.cleanup()
    raw_wav.close()
    processed_wav.close()

    print(f"\n\nCapture complete!")
    print(f"  Total chunks: {chunk_count[0]}")
    print(f"  Raw frames: {total_raw_frames[0]:,}")
    print(f"  Processed frames: {total_processed_frames[0]:,}")
    print(f"\nFiles saved:")
    print(f"  Raw (mic input):       {raw_file}")
    print(f"  Processed (to Vosk):   {processed_file}")

    # Analyze the files
    print(f"\n{'='*60}")
    print("Analysis:")
    print(f"{'='*60}")

    with wave.open(str(raw_file), "rb") as wf:
        print(f"\nRaw capture:")
        print(f"  Sample rate: {wf.getframerate()} Hz")
        print(f"  Channels: {wf.getnchannels()}")
        print(f"  Frames: {wf.getnframes():,}")
        print(f"  Duration: {wf.getnframes() / wf.getframerate():.2f} sec")

    with wave.open(str(processed_file), "rb") as wf:
        print(f"\nProcessed (sent to Vosk):")
        print(f"  Sample rate: {wf.getframerate()} Hz")
        print(f"  Channels: {wf.getnchannels()}")
        print(f"  Frames: {wf.getnframes():,}")
        print(f"  Duration: {wf.getnframes() / wf.getframerate():.2f} sec")

        # Read and check audio
        audio_data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
        print(f"  RMS: {rms:.2f}")

        if rms < 100:
            print(f"  ⚠️  WARNING: Audio is very quiet or silent!")

    print(f"\nTo listen to the files:")
    print(f"  play {raw_file}")
    print(f"  play {processed_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test daemon audio capture")
    parser.add_argument(
        "--duration",
        type=float,
        default=3.0,
        help="Recording duration in seconds (default: 3.0)",
    )
    args = parser.parse_args()

    test_daemon_style_capture(duration=args.duration)
