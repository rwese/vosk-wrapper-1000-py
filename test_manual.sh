#!/bin/bash

# This script helps you test the vosk-wrapper manually
# You'll have time to speak between start and stop

echo "=== Cleaning up old processes ==="
pkill -9 -f "vosk-wrapper-1000" 2>/dev/null || true
sleep 2

echo "=== Starting daemon in foreground ==="
echo "Logs will appear here..."
uv run vosk-wrapper-1000 daemon --foreground --device "AnkerWork" 2>&1 &
DAEMON_PID=$!
echo "Daemon PID: $DAEMON_PID"

echo ""
echo "=== Waiting 15 seconds for daemon to load model ==="
sleep 15

echo ""
echo "=== Sending START signal ==="
uv run vosk-wrapper-1000 start default

echo ""
echo "==============================================="
echo "SPEAK NOW INTO YOUR ANKERWORK MICROPHONE!"
echo "You have 10 seconds..."
echo "==============================================="
sleep 10

echo ""
echo "=== Sending STOP signal ==="
uv run vosk-wrapper-1000 stop default

echo ""
echo "=== Waiting for final output ==="
sleep 2

echo ""
echo "=== Killing daemon ==="
kill -TERM $DAEMON_PID 2>/dev/null || true
sleep 1

echo ""
echo "=== Test complete ==="
echo "Check the output above for recognized text"
