#!/usr/bin/env python3
"""
Quick fix for audio recording issues.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from vosk_wrapper_1000.config_manager import ConfigManager


def main():
    print("QUICK AUDIO FIX")
    print("=" * 50)

    # Load current config
    config_manager = ConfigManager()
    config = config_manager.load_config()

    print("Current issues identified:")
    print("1. Your default_device is empty - using system default (device 0)")
    print("2. Device 0 only supports 48000 Hz, but system tries 16000 Hz")
    print("3. Device 2 supports 16000 Hz but has channel issues")

    print("\nRecommended fixes:")
    print("Option 1: Use device 0 with 48000 Hz (recommended)")
    print("  - Change default_device to '0' in config")
    print("  - This will use resampling from 48000 to model rate")

    print("\nOption 2: Try device 2 with channel fix")
    print("  - Change default_device to '2' in config")
    print("  - May need additional channel configuration")

    print("\nOption 3: Lower silence threshold")
    print("  - Your current threshold: 350.0 (very high)")
    print("  - Try changing to 50.0 for testing")

    # Apply quick fix
    print("\n" + "=" * 50)
    print("APPLYING QUICK FIX...")
    print("=" * 50)

    # Fix 1: Set device to 0 explicitly
    config.audio.default_device = "0"

    # Fix 2: Lower silence threshold for testing
    config.audio.silence_threshold = 50.0

    # Save config
    try:
        config_manager.save_config(config)
        print("✓ Configuration updated successfully!")
        print(f"  - Default device set to: {config.audio.default_device}")
        print(f"  - Silence threshold lowered to: {config.audio.silence_threshold}")

        print("\nNow try running vosk-wrapper-1000 again:")
        print("  vosk-wrapper-1000 daemon --foreground")
        print("  vosk-wrapper-1000 start")

    except Exception as e:
        print(f"✗ Failed to save config: {e}")
        return False

    return True


if __name__ == "__main__":
    main()
