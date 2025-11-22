#!/usr/bin/env python3
"""Device management utilities for vosk-wrapper-1000."""

import sys
from typing import Dict, List, Optional, Tuple

import sounddevice as sd

from .audio_system import validate_device_compatibility


class DeviceManager:
    """Manages audio device detection and validation."""

    def __init__(self):
        self.devices_cache: Optional[List[Dict]] = None

    def refresh_devices(self) -> List[Dict]:
        """Refresh list of available audio devices."""
        try:
            devices = sd.query_devices()
            input_devices = []

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
                    input_devices.append(device_info)

            self.devices_cache = input_devices
            return input_devices
        except Exception as e:
            print(f"Error refreshing devices: {e}", file=sys.stderr)
            return []

    def get_device_info(self, device_arg: Optional[str]) -> Optional[Dict]:
        """Get device info by name or ID."""
        if self.devices_cache is None:
            self.refresh_devices()

        # If no device specified, return None (will use default)
        if device_arg is None:
            return None

        # Try to find by ID first
        device_id = None
        try:
            device_id = int(device_arg)
        except ValueError:
            pass

        if device_id is not None and self.devices_cache:
            for device in self.devices_cache:
                if device["id"] == device_id:
                    return device

        # If not found by ID, try by name
        if self.devices_cache:
            for device in self.devices_cache:
                if device_arg.lower() in device["name"].lower():
                    return device
        return None

    def get_device_by_id(self, device_id: int) -> Optional[Dict]:
        """Get device by ID."""
        if self.devices_cache is None:
            self.refresh_devices()

        if self.devices_cache:
            for device in self.devices_cache:
                if device["id"] == device_id:
                    return device
        return None

    def validate_device_for_model(
        self, device_id: int, model_sample_rate: int
    ) -> Tuple[bool, str]:
        """Validate device compatibility with model sample rate."""
        return validate_device_compatibility(device_id, model_sample_rate)

    def print_device_list(self):
        """Print formatted list of available devices."""
        devices = self.refresh_devices()

        if not devices:
            print("No audio input devices found!", file=sys.stderr)
            print("\nTroubleshooting steps:", file=sys.stderr)
            print("1. Check microphone is connected and not muted", file=sys.stderr)
            print("2. Grant microphone permissions to Terminal/Python", file=sys.stderr)
            print("3. Close other apps using the microphone", file=sys.stderr)
            print("\nmacOS Microphone Permissions:", file=sys.stderr)
            print(
                "  System Preferences → Security & Privacy → Privacy → Microphone",
                file=sys.stderr,
            )
            print("  Enable Terminal (or your terminal application)", file=sys.stderr)
            return

        print("Available Audio Input Devices:", file=sys.stderr)
        print(
            f"{'ID':<4} {'Name':<40} {'Channels':<10} {'Sample Rate':<12} {'Host API':<15}",
            file=sys.stderr,
        )
        print("-" * 85, file=sys.stderr)

        for device in devices:
            name = (
                device["name"][:38] + ".."
                if len(device["name"]) > 40
                else device["name"]
            )
            rate_str = f"{device['default_samplerate']:.0f} Hz"

            print(
                f"{device['id']:<4} {name:<40} {device['max_input_channels']:<10} {rate_str:<12} {device['host_api']:<15}",
                file=sys.stderr,
            )
