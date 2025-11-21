#!/usr/bin/env python3
"""Simple audio capture test script to validate audio backend without Vosk."""

import sys
import time
import signal
import argparse
import queue
import numpy as np


def main():
    parser = argparse.ArgumentParser(description="Test audio capture")
    parser.add_argument(
        "--device",
        type=str,
        help="Audio device name or substring to match"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=10,
        help="Recording duration in seconds (default: 10)"
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio devices and exit"
    )

    args = parser.parse_args()

    # Import sounddevice
    try:
        import sounddevice as sd
    except ImportError:
        print("Error: sounddevice not installed. Install with: pip install sounddevice")
        return 1

    # List devices if requested
    if args.list_devices:
        print("Available audio devices:")
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                print(f"  {idx}: {dev['name']} (inputs: {dev['max_input_channels']}, "
                      f"sample rate: {dev['default_samplerate']})")
        return 0

    # Find device if specified
    device_idx = None
    if args.device:
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0 and args.device.lower() in dev['name'].lower():
                device_idx = idx
                print(f"Found device: {dev['name']} (index: {idx})")
                break

        if device_idx is None:
            print(f"Error: Could not find device matching '{args.device}'")
            print("\nAvailable input devices:")
            for idx, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    print(f"  {idx}: {dev['name']}")
            return 1
    else:
        # Use default device
        device_idx = sd.default.device[0]  # Input device
        dev = sd.query_devices(device_idx)
        print(f"Using default device: {dev['name']} (index: {device_idx})")

    # Get device info and use its native sample rate
    device_info = sd.query_devices(device_idx)
    sample_rate = int(device_info['default_samplerate'])
    blocksize = sample_rate // 2  # 0.5 second chunks
    channels = 1

    print(f"\nDevice: {device_info['name']}")
    print(f"Sample rate: {sample_rate} Hz (device native)")
    print(f"Channels: {channels}")
    print(f"Block size: {blocksize} frames ({blocksize/sample_rate:.2f}s)")
    print()

    # Track audio statistics
    chunk_count = 0
    total_frames = 0
    error_count = 0
    audio_queue = queue.Queue()
    start_time = None
    running = True

    def audio_callback(indata, frames, time_info, status):
        nonlocal chunk_count, total_frames, error_count

        if status:
            print(f"Status: {status}")
            error_count += 1

        chunk_count += 1
        total_frames += frames
        # RawInputStream provides a buffer, convert to bytes to get length
        byte_count = len(bytes(indata))
        audio_queue.put((frames, byte_count))

    def signal_handler(signum, frame):
        nonlocal running
        print("\nStopping...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"Recording for {args.duration} seconds...")
    print("Press Ctrl+C to stop early\n")

    try:
        # Start the audio stream
        with sd.RawInputStream(
            samplerate=sample_rate,
            blocksize=blocksize,
            device=device_idx,
            dtype='int16',
            channels=channels,
            callback=audio_callback
        ) as stream:
            start_time = time.time()
            print("Stream started successfully!")
            print()

            # Read audio chunks
            last_report = start_time
            while running and (time.time() - start_time) < args.duration:
                try:
                    frames, byte_count = audio_queue.get(timeout=0.1)

                    # Print progress every second
                    elapsed = time.time() - start_time
                    if elapsed - last_report >= 1.0:
                        total_bytes = total_frames * 2  # int16 = 2 bytes
                        mb_per_sec = (total_bytes / elapsed) / (1024 * 1024)
                        print(f"[{elapsed:.1f}s] Chunks: {chunk_count}, "
                              f"Frames: {total_frames}, "
                              f"Rate: {mb_per_sec:.2f} MB/s, "
                              f"Errors: {error_count}")
                        last_report = elapsed

                except queue.Empty:
                    continue

            elapsed = time.time() - start_time

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Print summary
    total_bytes = total_frames * 2  # int16 = 2 bytes
    print("\n" + "=" * 60)
    print("RECORDING COMPLETE")
    print("=" * 60)
    print(f"Duration: {elapsed:.2f} seconds")
    print(f"Chunks received: {chunk_count}")
    print(f"Frames received: {total_frames}")
    print(f"Total data: {total_bytes / 1024:.1f} KB ({total_bytes / (1024*1024):.2f} MB)")
    print(f"Average rate: {(total_bytes / elapsed) / (1024*1024):.2f} MB/s")
    print(f"Errors: {error_count}")

    if chunk_count > 0:
        expected_chunks = int(elapsed * sample_rate / blocksize)
        chunk_ratio = (chunk_count / expected_chunks) * 100
        print(f"Expected chunks: ~{expected_chunks}")
        print(f"Chunk ratio: {chunk_ratio:.1f}%")

        if chunk_ratio < 90:
            print("\n⚠️  WARNING: Receiving fewer chunks than expected!")
            print("   This may indicate audio capture issues.")
        elif chunk_ratio > 110:
            print("\n⚠️  WARNING: Receiving more chunks than expected!")
            print("   This may indicate timing issues.")
        else:
            print("\n✓ Audio capture appears to be working correctly!")
    else:
        print("\n✗ ERROR: No audio chunks received!")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
