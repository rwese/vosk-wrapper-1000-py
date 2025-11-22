#!/usr/bin/env python3
"""
Final test to identify the audio callback issue.
Tests the main application flow directly without imports.
"""

import os


def test_main_app_directly():
    """Test the main application by calling run_service directly"""
    print("🔍 TESTING MAIN APPLICATION DIRECTLY")
    print("=" * 60)

    try:
        # Import and run the main service function directly
        import argparse

        from vosk_wrapper_1000.main import run_service

        print("🚀 Starting main application...")

        # Create mock args object
        args = argparse.Namespace()
        args.record_audio = "/tmp/direct_test.wav"
        args.device = "1"
        args.model = "/Users/wese/.local/share/vosk-wrapper-1000/models/vosk-model-small-en-us-0.15"
        args.name = "test"
        args.noise_reduction = 0.2
        args.stationary_noise = True
        args.non_stationary_noise = False
        args.disable_noise_filter = False
        args.foreground = True
        args.words = False
        args.partial_words = False
        args.grammar = None
        args.hooks_dir = None
        args.list_devices = False

        # This will run the exact same code path as the real app
        run_service(args)

    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Check if test file was created
        if os.path.exists("/tmp/direct_test.wav"):
            size = os.path.getsize("/tmp/direct_test.wav")
            print(f"📄 Test file size: {size} bytes")
            if size > 100:  # More than just header
                print("✅ SUCCESS: Audio data was recorded!")
            else:
                print("❌ FAILURE: Only header written")
        else:
            print("❌ FAILURE: No test file created")


if __name__ == "__main__":
    test_main_app_directly()
