#!/bin/bash

set -e

echo "=== Cleaning up old processes ==="
pkill -9 -f "vosk-wrapper-1000" 2>/dev/null || true
sleep 2

echo "=== Starting daemon in background ==="
uv run vosk-wrapper-1000 daemon --foreground --device "AnkerWork" 2>&1 | grep -v "^LOG" &
DAEMON_PID=$!
echo "Daemon PID: $DAEMON_PID"

echo "=== Waiting for daemon to initialize (15s) ==="
sleep 15

echo ""
echo "=== Sending START signal ==="
uv run vosk-wrapper-1000 start default

echo ""
echo "=== Listening for 5 seconds - please speak now ==="
sleep 5

echo ""
echo "=== Sending STOP signal ==="
uv run vosk-wrapper-1000 stop default

sleep 2

echo ""
echo "=== Terminating daemon ==="
kill -TERM $DAEMON_PID 2>/dev/null || true
wait $DAEMON_PID 2>/dev/null || true

echo ""
echo "=== Test complete ==="
