#!/usr/bin/env python3
"""
Fix audio configuration to use working device.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from vosk_wrapper_1000.config_manager import ConfigManager


def main():
    print("FIXING AUDIO CONFIGURATION")
    print("=" * 50)

    # Load current config
    config_manager = ConfigManager()
    config = config_manager.load_config()

    print("Setting device to 4 (supports 16000 Hz natively)...")
    config.audio.default_device = "4"

    # Also set a reasonable silence threshold
    config.audio.silence_threshold = 50.0

    try:
        config_manager.save_config(config)
        print("✓ Configuration updated!")
        print(f"  - Device set to: {config.audio.default_device}")
        print(f"  - Silence threshold: {config.audio.silence_threshold}")

        print("\nNow test with:")
        print("  vosk-wrapper-1000 daemon --foreground")
        print("  # Wait for it to start")
        print("  vosk-wrapper-1000 start")
        print("  # Speak into microphone - should work now!")

    except Exception as e:
        print(f"✗ Failed to save config: {e}")
        return False

    return True


if __name__ == "__main__":
    main()
