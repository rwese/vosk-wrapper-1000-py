#!/usr/bin/env python3
"""
Diagnose audio recording issues in vosk-wrapper-1000.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    import sounddevice as sd

    print("✓ sounddevice imported successfully")
except ImportError as e:
    print(f"✗ Failed to import sounddevice: {e}")
    print("  Try: pip install sounddevice")
    sys.exit(1)

try:
    from vosk_wrapper_1000.device_manager import DeviceManager

    print("✓ DeviceManager imported successfully")
except ImportError as e:
    print(f"✗ Failed to import DeviceManager: {e}")
    sys.exit(1)


def check_audio_system():
    """Check audio system information."""
    print("\n" + "=" * 60)
    print("AUDIO SYSTEM DIAGNOSTICS")
    print("=" * 60)

    try:
        # Check audio devices
        devices = sd.query_devices()
        print(f"\nFound {len(devices)} audio devices:")

        input_devices = [d for d in devices if d["max_input_channels"] > 0]
        print(f"  {len(input_devices)} input devices:")

        for i, device in enumerate(input_devices):
            print(f"    [{i}] {device['name']}")
            print(f"        Channels: {device['max_input_channels']}")
            print(f"        Sample Rate: {device['default_samplerate']}")
            print(f"        Host API: {device['hostapi']}")

        # Check default device
        default_input = sd.default.device[0]
        if default_input >= 0 and default_input < len(devices):
            default_device = devices[default_input]
            print(f"\nDefault input device: [{default_input}] {default_device['name']}")
        else:
            print(f"\nDefault input device: {default_input} (invalid!)")

    except Exception as e:
        print(f"✗ Error querying devices: {e}")
        return False

    return True


def test_device_access():
    """Test if we can access the configured device."""
    print("\n" + "=" * 60)
    print("DEVICE ACCESS TEST")
    print("=" * 60)

    try:
        # Load user's config
        from vosk_wrapper_1000.config_manager import ConfigManager

        config_manager = ConfigManager()
        config = config_manager.load_config()

        device_id = None
        if config.audio.default_device and config.audio.default_device != "":
            try:
                device_id = int(config.audio.default_device)
                print(f"Configured device ID: {device_id}")
            except ValueError:
                device_id = config.audio.default_device
                print(f"Configured device name: {device_id}")
        else:
            device_id = None
            print("Using default device")

        # Get device info
        device_manager = DeviceManager()
        device_info = device_manager.get_device_info(device_id)

        if device_info:
            print(f"Device info:")
            print(f"  Name: {device_info['name']}")
            print(f"  ID: {device_info['id']}")
            print(f"  Channels: {device_info['max_input_channels']}")
            print(f"  Sample Rate: {device_info['default_samplerate']}")
        else:
            print("✗ Could not get device info!")
            return False

    except Exception as e:
        print(f"✗ Error getting device info: {e}")
        return False

    return True


def test_audio_stream():
    """Test creating an audio stream."""
    print("\n" + "=" * 60)
    print("AUDIO STREAM TEST")
    print("=" * 60)

    try:
        # Load user's config
        from vosk_wrapper_1000.config_manager import ConfigManager

        config_manager = ConfigManager()
        config = config_manager.load_config()

        device_id = None
        if config.audio.default_device and config.audio.default_device != "":
            try:
                device_id = int(config.audio.default_device)
            except ValueError:
                pass

        # Test stream creation
        print("Creating audio stream...")

        def test_callback(indata, frames, time, status):
            if status:
                print(f"  Stream status: {status}")
            else:
                # Check if we're getting audio data
                if len(indata) > 0:
                    max_val = abs(indata).max()
                    if max_val > 0:
                        print(f"  ✓ Audio detected! Max value: {max_val:.6f}")
                    else:
                        print("  ✓ Stream active, but audio is silent")

        stream = sd.InputStream(
            samplerate=16000,
            blocksize=1024,
            device=device_id,
            dtype="int16",
            channels=1,
            callback=test_callback,
        )

        print("✓ Stream created successfully!")
        print("Testing audio capture for 5 seconds...")
        print("(Speak into your microphone or make some noise)")

        stream.start()

        import time

        start_time = time.time()
        audio_detected = False

        while time.time() - start_time < 5:
            time.sleep(0.1)

        stream.stop()
        stream.close()

        print("✓ Stream test completed")

    except Exception as e:
        print(f"✗ Error with audio stream: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def check_permissions():
    """Check for common permission issues."""
    print("\n" + "=" * 60)
    print("PERMISSIONS CHECK")
    print("=" * 60)

    # Check if we're in a container/sandbox
    if os.path.exists("/.dockerenv"):
        print("⚠ Running in Docker container")
        print("  Audio may not work without proper device access")

    # Check for PulseAudio/PipeWire
    if os.system("which pactl > /dev/null 2>&1") == 0:
        print("✓ PulseAudio available")
        try:
            result = os.popen("pactl info").read()
            if "Default Sink" in result:
                print("✓ PulseAudio seems to be running")
            else:
                print("⚠ PulseAudio may not be running properly")
        except:
            print("⚠ Could not check PulseAudio status")

    if os.system("which pw-cli > /dev/null 2>&1") == 0:
        print("✓ PipeWire available")
        try:
            result = os.popen("pw-cli info").read()
            if "core" in result.lower():
                print("✓ PipeWire seems to be running")
            else:
                print("⚠ PipeWire may not be running properly")
        except:
            print("⚠ Could not check PipeWire status")

    # Check audio device permissions
    audio_devices = ["/dev/snd/*", "/dev/dsp*", "/dev/audio*"]
    for pattern in audio_devices:
        try:
            result = os.popen(f"ls -la {pattern} 2>/dev/null").read()
            if result:
                print(f"✓ Audio devices found: {pattern}")
        except:
            pass


def main():
    """Run all diagnostics."""
    print("VOSK-WRAPPER-1000 AUDIO DIAGNOSTICS")
    print("This script will help identify why audio recording isn't working.")

    success = True
    success &= check_audio_system()
    success &= test_device_access()
    success &= test_audio_stream()
    check_permissions()

    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)

    if success:
        print("✓ Basic audio functionality appears to be working")
        print("\nIf you're still not getting audio, check:")
        print("  1. Microphone hardware connection")
        print("  2. System audio/mixer settings")
        print("  3. Application permissions (microphone access)")
        print("  4. Silence threshold in config (currently 350.0)")
        print("     - Try lowering to 50.0 for testing")
        print(
            "  5. Run vosk-wrapper-1000 with --list-devices to verify device selection"
        )
    else:
        print("✗ Issues found with audio system")
        print(
            "\nPlease check the errors above and fix them before using vosk-wrapper-1000"
        )

    print(f"\nYour current silence threshold: 350.0")
    print("This is quite high - try lowering it if you have quiet audio input")


if __name__ == "__main__":
    main()
