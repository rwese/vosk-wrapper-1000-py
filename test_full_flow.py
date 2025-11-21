#!/usr/bin/env python3
"""Test full flow like main.py."""

import signal
import sys
import time
import sounddevice as sd
import vosk
import os

print("1. Loading Vosk model...")
sys.stdout.flush()
model = vosk.Model("/home/rweselowski/.local/share/vosk-wrapper-1000/models/vosk-model-en-us-0.22-lgraph")
print("✓ Model loaded")

print("2. Setting up signal handlers...")
listening = False

def signal_handler(sig, frame):
    global listening
    print(f"Got signal {sig}")
    if sig == signal.SIGUSR1:
        listening = True

signal.signal(signal.SIGUSR1, signal_handler)
signal.signal(signal.SIGINT, lambda s,f: sys.exit(0))
print("✓ Signal handlers installed")

print(f"3. My PID: {os.getpid()}")
print("4. Waiting for SIGUSR1 signal...")
sys.stdout.flush()

while not listening:
    time.sleep(0.1)

print("5. Signal received, creating stream...")
sys.stdout.flush()

try:
    stream = sd.RawInputStream(
        samplerate=48000,
        blocksize=8000,
        device=7,
        dtype='int16',
        channels=1,
        callback=lambda *args: None
    )
    print("✓ Stream created!")
    stream.start()
    print("✓ Stream started!")
    time.sleep(2)
    stream.stop()
    stream.close()
    print("✓ Test passed!")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
