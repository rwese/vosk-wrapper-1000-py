"""Audio system detection and information utilities."""

import platform
import subprocess
import sys
from typing import Dict, List, Tuple


def detect_audio_system() -> Dict[str, str]:
    """Detect the audio system and related information."""
    system = platform.system()
    audio_info = {
        "platform": system,
        "audio_system": "unknown",
        "audio_backend": "sounddevice",
        "details": {},
    }

    if system == "Linux":
        audio_info.update(_detect_linux_audio())
    elif system == "Darwin":  # macOS
        audio_info.update(_detect_macos_audio())
    elif system == "Windows":
        audio_info.update(_detect_windows_audio())

    return audio_info


def _detect_linux_audio() -> Dict[str, str]:
    """Detect Linux audio system."""
    audio_info = {"audio_system": "unknown", "details": {}}

    # Check for PipeWire
    try:
        result = subprocess.run(
            ["pgrep", "-x", "pipewire"], capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            audio_info["audio_system"] = "pipewire"
            audio_info["audio_backend"] = (
                "pipewire-python (preferred) / sounddevice (fallback)"
            )

            # Get PipeWire version
            try:
                pw_version = subprocess.run(
                    ["pipewire", "--version"], capture_output=True, text=True, timeout=2
                )
                if pw_version.returncode == 0:
                    audio_info["details"]["pipewire_version"] = (
                        pw_version.stdout.strip()
                    )
            except:
                pass

            # Check if pipewire-python is available
            try:
                import pipewire_python

                audio_info["details"]["pipewire_python_available"] = True
                audio_info["audio_backend"] = "pipewire-python"
            except ImportError:
                audio_info["details"]["pipewire_python_available"] = False
                audio_info["details"]["pipewire_python_install"] = (
                    "pip install pipewire-python"
                )

            return audio_info
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Check for PulseAudio
    try:
        result = subprocess.run(
            ["pgrep", "-x", "pulseaudio"], capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            audio_info["audio_system"] = "pulseaudio"
            audio_info["audio_backend"] = "sounddevice (via PulseAudio)"

            # Get PulseAudio version
            try:
                pa_version = subprocess.run(
                    ["pulseaudio", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if pa_version.returncode == 0:
                    audio_info["details"]["pulseaudio_version"] = (
                        pa_version.stdout.strip()
                    )
            except:
                pass

            return audio_info
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Check for ALSA
    try:
        result = subprocess.run(
            ["aplay", "-l"], capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            audio_info["audio_system"] = "alsa"
            audio_info["audio_backend"] = "sounddevice (via ALSA)"
            audio_info["details"]["alsa_cards"] = result.stdout.count("card")
            return audio_info
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    audio_info["audio_system"] = "unknown"
    audio_info["audio_backend"] = "sounddevice (default)"
    return audio_info


def _detect_macos_audio() -> Dict[str, str]:
    """Detect macOS audio system."""
    audio_info = {
        "audio_system": "coreaudio",
        "audio_backend": "sounddevice (via CoreAudio)",
        "details": {},
    }

    # Get macOS version
    try:
        result = subprocess.run(
            ["sw_vers", "-productVersion"], capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            audio_info["details"]["macos_version"] = result.stdout.strip()
    except:
        pass

    # Check audio devices with system_profiler
    try:
        result = subprocess.run(
            ["system_profiler", "SPAudioDataType"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Count audio devices
            device_count = result.stdout.count("Audio Device:")
            audio_info["details"]["audio_devices"] = device_count
    except:
        pass

    return audio_info


def _detect_windows_audio() -> Dict[str, str]:
    """Detect Windows audio system."""
    audio_info = {
        "audio_system": "wasapi",
        "audio_backend": "sounddevice (via WASAPI)",
        "details": {},
    }

    # Get Windows version
    try:
        result = subprocess.run(
            ["ver"], capture_output=True, text=True, timeout=2, shell=True
        )
        if result.returncode == 0:
            audio_info["details"]["windows_version"] = result.stdout.strip()
    except:
        pass

    # Check for PowerShell to get more audio info
    try:
        ps_command = "Get-WmiObject -Class Win32_SoundDevice | Select-Object Name"
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            devices = [
                line.strip()
                for line in result.stdout.split("\n")
                if line.strip() and "Name" not in line
            ]
            audio_info["details"]["audio_devices"] = len(devices)
    except:
        pass

    return audio_info


def print_audio_system_info():
    """Print comprehensive audio system information."""
    audio_info = detect_audio_system()

    print("=== Audio System Information ===", file=sys.stderr)
    print(f"Platform: {audio_info['platform']}", file=sys.stderr)
    print(f"Audio System: {audio_info['audio_system']}", file=sys.stderr)
    print(f"Audio Backend: {audio_info['audio_backend']}", file=sys.stderr)

    if audio_info["details"]:
        print("Details:", file=sys.stderr)
        for key, value in audio_info["details"].items():
            if key == "pipewire_python_install":
                print(f"  {key.replace('_', ' ').title()}: {value}", file=sys.stderr)
            else:
                print(f"  {key.replace('_', ' ').title()}: {value}", file=sys.stderr)

    print("-" * 40, file=sys.stderr)


def get_audio_device_info() -> List[Dict[str, any]]:
    """Get detailed information about available audio devices."""
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        device_list = []

        for i, device in enumerate(devices):
            if device["max_input_channels"] > 0:  # Only input devices
                device_info = {
                    "id": i,
                    "name": device["name"],
                    "max_input_channels": device["max_input_channels"],
                    "max_output_channels": device["max_output_channels"],
                    "default_samplerate": device["default_samplerate"],
                    "host_api": device.get("host_api", "Unknown"),
                }

                # Try to get supported sample rates (not always available)
                try:
                    supported_rates = sd.check_input_settings(
                        device=i, samplerate=device["default_samplerate"]
                    )
                    device_info["supported_rates"] = [device["default_samplerate"]]
                except:
                    device_info["supported_rates"] = ["Unknown"]

                device_list.append(device_info)

        return device_list

    except Exception as e:
        print(f"Error getting device info: {e}", file=sys.stderr)
        return []


def print_device_list():
    """Print detailed device information."""
    print_audio_system_info()

    devices = get_audio_device_info()

    if not devices:
        print("No audio input devices found!", file=sys.stderr)
        return

    print("Available Audio Input Devices:", file=sys.stderr)
    print(
        f"{'ID':<4} {'Name':<40} {'Channels':<10} {'Sample Rate':<12} {'Host API':<15}",
        file=sys.stderr,
    )
    print("-" * 85, file=sys.stderr)

    for device in devices:
        name = (
            device["name"][:38] + ".." if len(device["name"]) > 40 else device["name"]
        )
        rate_str = f"{device['default_samplerate']:.0f} Hz"

        print(
            f"{device['id']:<4} {name:<40} {device['max_input_channels']:<10} {rate_str:<12} {device['host_api']:<15}",
            file=sys.stderr,
        )


def validate_device_compatibility(
    device_id: int, target_samplerate: int
) -> Tuple[bool, str]:
    """Validate if a device supports the target sample rate."""
    try:
        import sounddevice as sd

        # Get device info
        device_info = sd.query_devices(device_id)
        device_rate = int(device_info["default_samplerate"])

        # Check if we can create a stream with the target rate
        try:
            # Test with a dummy callback
            def dummy_callback(indata, frames, time, status):
                pass

            test_stream = sd.RawInputStream(
                samplerate=device_rate,  # Use device's native rate
                blocksize=1024,
                device=device_id,
                dtype="int16",
                channels=1,
                callback=dummy_callback,
            )
            test_stream.close()

            return (
                True,
                f"Device supports {device_rate} Hz (will resample to {target_samplerate} Hz)",
            )

        except Exception as e:
            return False, f"Device stream creation failed: {e}"

    except Exception as e:
        return False, f"Device validation failed: {e}"
