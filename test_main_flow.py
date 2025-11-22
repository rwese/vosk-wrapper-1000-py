#!/usr/bin/env python3
"""
Simple test to check if the issue is in the main application flow.
"""

import os
import signal
import sys
import time


# Simple signal manager for testing
class TestSignalManager:
    def __init__(self):
        self.running = True
        self.listening = False

    def is_running(self):
        return self.running

    def is_listening(self):
        return self.listening

    def _handle_start(self, sig, frame):
        print("Received SIGUSR1: Starting listening...")
        self.listening = True

    def _handle_stop(self, sig, frame):
        print("Received SIGUSR2: Stopping listening...")
        self.listening = False

    def _handle_terminate(self, sig, frame):
        print(f"Received signal {sig}: Terminating...")
        self.running = False
        self.listening = False


# Mock Args class
class MockArgs:
    """Mock arguments for testing."""

    def __init__(self):
        self.record_audio = "/tmp/test_main_flow.wav"
        self.device = "1"
        self.model = "/Users/wese/.local/share/vosk-wrapper-1000/models/vosk-model-small-en-us-0.15"
        self.name = "test"
        self.foreground = True
        self.noise_reduction = 0.2
        self.disable_noise_filter = False
        self.stationary_noise = True
        self.words = False
        self.partial_words = False
        self.grammar = None
        self.hooks_dir = None


# Test the exact flow from main.py
def test_main_flow():
    print("🔍 TESTING MAIN APPLICATION FLOW")
    print("=" * 50)

    # Setup exactly like main.py
    args = MockArgs()

    signal_manager = TestSignalManager()

    # Mock the managers
    class MockModelManager:
        def get_model_sample_rate(self, model_path):
            return 16000

    class MockDeviceManager:
        def __init__(self):
            pass

        def refresh_devices(self):
            return [
                {
                    "id": 1,
                    "name": "MacBook Pro Microphone",
                    "max_input_channels": 1,
                    "default_samplerate": 44100,
                }
            ]

        def get_device_info(self, device_arg):
            if device_arg == "1":
                return {
                    "id": 1,
                    "name": "MacBook Pro Microphone",
                    "default_samplerate": 44100,
                }
            return None

    class MockAudioProcessor:
        def __init__(self):
            self.device_rate = 44100
            self.model_rate = 16000

        def process_audio_chunk(self, audio_data):
            return audio_data  # Pass through unchanged

    class MockAudioRecorder:
        def __init__(self, filename, sample_rate):
            self.filename = filename
            self.sample_rate = sample_rate
            self.file = None

        def start_recording(self):
            import wave

            self.file = wave.open(self.filename, "wb")
            self.file.setsampwidth(2)
            self.file.setframerate(self.sample_rate)
            self.file.setnchannels(1)
            return True

        def write_audio(self, audio_data):
            if self.file:
                self.file.writeframes(audio_data.tobytes())

    class MockHookManager:
        def __init__(self, hooks_dir):
            pass

        def execute_hooks(self, hook_type, text=""):
            pass

    _model_manager = MockModelManager()
    device_manager = MockDeviceManager()
    audio_processor = MockAudioProcessor()
    audio_recorder = MockAudioRecorder(args.record_audio, 16000)
    _hook_manager = MockHookManager(args.hooks_dir)

    # Test the exact callback from main.py
    def audio_callback(indata, frames, time, status):
        """Audio callback for sounddevice."""
        if status:
            print(f"Status: {status}", file=sys.stderr)
            sys.stderr.flush()

        # Debug: Print signal manager state
        if frames % 100 == 0:
            listening_state = signal_manager.is_listening()
            print(
                f"CALLBACK: frames={frames}, listening={listening_state}, max={indata.max():.6f}",
                file=sys.stderr,
            )

        if signal_manager.is_listening():
            try:
                # Process audio through our pipeline
                processed_audio = audio_processor.process_audio_chunk(indata)

                # Save to recording file if enabled
                if args.record_audio:
                    audio_recorder.write_audio(processed_audio)

                print(f"✅ PROCESSED: frames={frames}, shape={indata.shape}")
                return True
            except Exception as e:
                print(f"❌ ERROR in callback: {e}")
                return False
        else:
            if frames % 100 == 0:
                print(
                    f"🚫 DROPPING: frames={frames}, listening={signal_manager.is_listening()}"
                )
            return False

    print("📡 STEP 1: Creating stream...")

    # Test stream creation exactly like main.py
    try:
        import sounddevice as sd

        device_info = device_manager.get_device_info(args.device)
        if device_info is None:
            device_id = None
            device_samplerate = None
        else:
            device_id = device_info["id"]
            device_samplerate = int(device_info["default_samplerate"])

        print(f"   Device ID: {device_id}")
        print(f"   Sample rate: {device_samplerate}")

        stream = sd.InputStream(
            samplerate=device_samplerate,
            blocksize=1024,
            device=device_id,
            dtype="int16",
            channels=1,
            callback=audio_callback,
        )

        print("✅ Stream created successfully")

    except Exception as e:
        print(f"❌ Stream creation failed: {e}")
        return False

    print("📢 STEP 2: Starting stream...")
    try:
        stream.start()
        print("✅ Stream started")
    except Exception as e:
        print(f"❌ Stream start failed: {e}")
        return False

    print("📡 STEP 3: Testing signals...")

    # Test signal handling
    def test_signal_handler(sig, frame):
        print(f"📡 Received {sig}")

    signal.signal(signal.SIGUSR1, test_signal_handler)
    signal.signal(signal.SIGUSR2, test_signal_handler)
    signal.signal(signal.SIGTERM, test_signal_handler)

    print("📤 STEP 4: Sending start signal...")
    os.kill(os.getpid(), signal.SIGUSR1)
    time.sleep(1)

    if signal_manager.is_listening():
        print("✅ Signal manager shows listening=True")
    else:
        print("❌ Signal manager shows listening=False")

    print("📤 STEP 5: Monitoring for 3 seconds...")

    callback_count = 0
    start_time = time.time()
    while time.time() - start_time < 3:
        time.sleep(0.1)
        if signal_manager.is_listening():
            callback_count += 1

    if callback_count > 0:
        print(f"✅ SUCCESS: Callback was called {callback_count} times")
    else:
        print("❌ FAILURE: Callback was never called")

    print("📥 STEP 6: Cleanup...")
    try:
        stream.stop()
        stream.close()
        print("✅ Stream stopped")
    except Exception as e:
        print(f"❌ Stream stop error: {e}")

    return callback_count > 0


if __name__ == "__main__":
    success = test_main_flow()
    if success:
        print("\n🎉 MAIN FLOW TEST PASSED!")
        print("The issue is NOT in the basic audio flow.")
        print("Problem is likely in:")
        print("1. Signal timing in main application")
        print("2. Different process environment")
        print("3. Race condition in main app")
    else:
        print("\n❌ MAIN FLOW TEST FAILED!")
        print("The basic audio flow has issues.")
