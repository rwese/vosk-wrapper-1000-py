#!/bin/bash
# Test script to verify daemon recording works correctly after the fix

set -e

echo "=========================================="
echo "Testing Daemon Recording After Fix"
echo "=========================================="

# Use test model
MODEL="vosk-model-en-gb-0.1"
TEMP_RECORDING="/tmp/test-daemon-recording-fixed.wav"

echo ""
echo "1. Starting daemon in background with recording enabled..."
echo "   Model: $MODEL (8000 Hz)"
echo "   Recording to: $TEMP_RECORDING"

# Start daemon in background
python -m vosk_wrapper_1000.main daemon \
    --name test-fix \
    --model "$MODEL" \
    --record-audio "$TEMP_RECORDING" \
    --log-level INFO \
    --foreground &

DAEMON_PID=$!
echo "   Daemon PID: $DAEMON_PID"

# Wait for daemon to start
sleep 2

echo ""
echo "2. Starting listening..."
python -m vosk_wrapper_1000.main send --name test-fix start
sleep 1

echo ""
echo "3. Recording for 5 seconds..."
echo "   (Please speak into your microphone)"
sleep 5

echo ""
echo "4. Stopping listening..."
python -m vosk_wrapper_1000.main send --name test-fix stop
sleep 1

echo ""
echo "5. Terminating daemon..."
python -m vosk_wrapper_1000.main terminate test-fix
sleep 1

# Make sure daemon is dead
kill $DAEMON_PID 2>/dev/null || true

echo ""
echo "6. Analyzing recording..."
python -c "
import wave
import numpy as np

with wave.open('$TEMP_RECORDING', 'rb') as wf:
    header_rate = wf.getframerate()
    frames = wf.getnframes()
    channels = wf.getnchannels()
    duration = frames / header_rate

    print(f'Recording Analysis:')
    print(f'  Sample rate:  {header_rate} Hz')
    print(f'  Channels:     {channels}')
    print(f'  Frames:       {frames:,}')
    print(f'  Duration:     {duration:.2f} seconds')

    # Read audio data
    audio_data = np.frombuffer(wf.readframes(frames), dtype=np.int16)
    rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
    print(f'  RMS:          {rms:.2f}')

    print()
    # Check expectations
    expected_rate = 8000  # Model rate for vosk-model-en-gb-0.1

    if header_rate == expected_rate:
        print('✓ Sample rate is correct!')
    else:
        print(f'✗ Sample rate mismatch! Expected {expected_rate} Hz, got {header_rate} Hz')

    if 4.0 < duration < 6.0:
        print('✓ Duration is reasonable for 5-second recording')
    else:
        print(f'✗ Duration seems wrong! Expected ~5 seconds, got {duration:.2f} seconds')

    if rms > 100:
        print('✓ Audio contains sound')
    else:
        print('⚠ Audio appears quiet or silent')
"

echo ""
echo "=========================================="
echo "Recording saved to: $TEMP_RECORDING"
echo "Listen with: play $TEMP_RECORDING"
echo "=========================================="
