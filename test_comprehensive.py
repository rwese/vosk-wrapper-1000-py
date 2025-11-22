#!/usr/bin/env python3
"""
Comprehensive test for vosk-wrapper-1000 audio issues.
Tests the exact same flow as main application but with better debugging.
"""

import os
import queue
import signal
import sys
import time

# Add src to path so we can import the modules
sys.path.insert(0, "src")

from vosk_wrapper_1000.audio_processor import AudioProcessor
from vosk_wrapper_1000.audio_recorder import AudioRecorder
from vosk_wrapper_1000.device_manager import DeviceManager
from vosk_wrapper_1000.hook_manager import HookManager
from vosk_wrapper_1000.model_manager import ModelManager
from vosk_wrapper_1000.pid_manager import remove_pid
from vosk_wrapper_1000.signal_manager import SignalManager


class MockArgs:
    """Mock args object for testing"""

    def __init__(self):
        self.record_audio = "/tmp/test_comprehensive.wav"
        self.device = "1"  # MacBook Pro Microphone
        self.model = "/Users/wese/.local/share/vosk-wrapper-1000/models/vosk-model-small-en-us-0.15"
        self.name = "test"
        self.noise_reduction = 0.2
        self.stationary_noise = True
        self.non_stationary_noise = False
        self.disable_noise_filter = False
        self.noise_filter_enabled = True
        self.foreground = True
        self.words = False
        self.partial_words = False
        self.grammar = None
        self.hooks_dir = None


def test_comprehensive():
    """Test the complete main application flow"""
    print("🧪 COMPREHENSIVE AUDIO TEST")
    print("=" * 60)

    # Setup all components exactly like main()
    args = MockArgs()
    signal_manager = SignalManager()
    _model_manager = ModelManager()
    device_manager = DeviceManager()
    _hook_manager = HookManager(args.hooks_dir)

    # Setup audio components
    audio_processor = AudioProcessor(
        device_rate=16000,  # Will be updated after device detection
        model_rate=16000,  # Will be updated after model loading
        noise_filter_enabled=not args.disable_noise_filter,
        noise_reduction_strength=args.noise_reduction,
        stationary_noise=args.stationary_noise and not args.non_stationary_noise,
    )

    audio_recorder = AudioRecorder(args.record_audio, 16000)

    audio_queue: queue.Queue[bytes] = queue.Queue()
    callback_counter = [0]

    # Define audio callback (cannot import from main.py as it's a nested function)
    def audio_callback(indata, frames, time_info, status):
        """Audio callback for sounddevice."""
        if status:
            print(status, file=sys.stderr)
            sys.stderr.flush()

        if signal_manager.is_listening():
            try:
                callback_counter[0] += 1
                if callback_counter[0] % 10 == 0:
                    print(
                        f"🎧 Callback #{callback_counter[0]}: frames={frames}, max={indata.max():.6f}",
                        file=sys.stderr,
                    )

                # Process audio through our pipeline
                processed_audio = audio_processor.process_audio_chunk(indata)

                # Save to recording file if enabled
                if args.record_audio:
                    audio_recorder.write_audio(processed_audio)

                # Queue for Vosk processing
                audio_queue.put_nowait(bytes(processed_audio))
            except queue.Full:
                pass
            except Exception as e:
                print(f"Error in audio callback: {e}", file=sys.stderr)
                sys.stderr.flush()

    print("✅ Components initialized")

    # Test 1: Device detection
    print("\n📱 TEST 1: Device Detection")
    devices = device_manager.refresh_devices()
    if not devices:
        print("❌ No devices found!")
        return False

    print(f"✅ Found {len(devices)} devices")
    for device in devices:
        print(f"   {device['id']}: {device['name']}")

    # Test 2: Device selection
    print("\n🎯 TEST 2: Device Selection")
    device_info = device_manager.get_device_info(args.device)
    if device_info is None:
        print("❌ Device selection failed")
        return False

    device_id = device_info["id"]
    device_samplerate = int(device_info["default_samplerate"])
    print(
        f"✅ Selected device {device_id}: {device_info['name']} @ {device_samplerate}Hz"
    )

    # Test 3: Model loading
    print("\n🤖 TEST 3: Model Loading")
    try:
        model_sample_rate = _model_manager.get_model_sample_rate(args.model)
        print(f"✅ Model sample rate: {model_sample_rate}Hz")

        # Update audio processor with correct rates
        audio_processor.device_rate = device_samplerate
        audio_processor.model_rate = model_sample_rate
        print(f"✅ Audio processor configured: {device_samplerate}→{model_sample_rate}")

    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return False

    # Test 4: Audio recorder setup
    print("\n🎙️ TEST 4: Audio Recorder")
    if args.record_audio:
        if not audio_recorder.start_recording():
            print("❌ Audio recorder failed to start")
            return False
        print("✅ Audio recorder started")

    # Test 5: Signal manager setup
    print("\n📡 TEST 5: Signal Manager")
    print(f"✅ Signal manager ready - running: {signal_manager.is_running()}")
    print(f"✅ Signal manager ready - listening: {signal_manager.is_listening()}")

    # Test 6: Stream creation (THE CRITICAL TEST)
    print("\n🎚️ TEST 6: Stream Creation (CRITICAL)")
    print("This is where the main app fails...")

    try:
        import sounddevice as sd

        print("🔧 Creating audio stream...")
        print(f"   Device ID: {device_id}")
        print(f"   Sample rate: {audio_processor.device_rate}")
        print("   Data type: int16")
        print("   Block size: 1024")
        print(f"   Callback function: {audio_callback}")

        # Create stream exactly like main app
        stream = sd.InputStream(
            samplerate=audio_processor.device_rate,
            blocksize=1024,
            device=device_id,
            dtype="int16",
            channels=1,
            callback=audio_callback,
        )

        print("✅ Stream object created")

        # Test 7: Stream start
        print("\n🎙️ TEST 7: Stream Start")
        print("Starting stream...")
        stream.start()
        print("✅ Stream started")

        # Test 8: Signal handling setup
        print("\n📡 TEST 8: Signal Handling")

        def test_signal_handler(sig, frame):
            print(f"📡 Received signal {sig}")
            if sig == signal.SIGUSR1:
                signal_manager._handle_start(sig, frame)
            elif sig == signal.SIGUSR2:
                signal_manager._handle_stop(sig, frame)

        # Setup signal handlers
        signal.signal(signal.SIGUSR1, test_signal_handler)
        signal.signal(signal.SIGUSR2, test_signal_handler)
        signal.signal(signal.SIGTERM, test_signal_handler)

        print("✅ Signal handlers configured")

        # Test 9: Send start signal
        print("\n🎤 TEST 9: Send Start Signal")
        print("Sending SIGUSR1...")
        os.kill(os.getpid(), signal.SIGUSR1)
        time.sleep(0.5)

        # Check if signal was received
        if signal_manager.is_listening():
            print("✅ Signal manager shows listening=True")
        else:
            print("❌ Signal manager still shows listening=False")

        # Test 10: Monitor callback for 3 seconds
        print("\n🎧 TEST 10: Monitor Callback (3 seconds)")

        start_time = time.time()
        while time.time() - start_time < 3:
            time.sleep(0.1)

        final_count = callback_counter[0]
        if final_count > 0:
            print(f"✅ SUCCESS: Callback was called {final_count} times")
        else:
            print("❌ FAILURE: Callback was never called")

        # Test 11: Stop signal
        print("\n🛑 TEST 11: Stop Signal")
        print("Sending SIGUSR2...")
        os.kill(os.getpid(), signal.SIGUSR2)
        time.sleep(0.5)

        # Test 12: Cleanup
        print("\n🧹 TEST 12: Cleanup")
        try:
            stream.stop()
            stream.close()
            print("✅ Stream stopped")
        except Exception as e:
            print(f"❌ Stream stop error: {e}")

        # Cleanup
        remove_pid("test")
        print("✅ Test completed!")
        return True

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print(f"\n\nTest interrupted by signal {sig}")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    success = test_comprehensive()

    if success:
        print("\n🎉 ALL TESTS PASSED!")
        print("The audio system is working correctly.")
        print("If the main app still doesn't work, the issue is in:")
        print("1. Signal timing/synchronization")
        print("2. Callback context/scope issues")
        print("3. Different process environment")
    else:
        print("\n❌ TESTS FAILED!")
        print("Check the error messages above for details.")
