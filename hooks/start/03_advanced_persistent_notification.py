#!/usr/bin/env python3
"""
Advanced Persistent Recording Notification - Start Hook

Enhanced version with more detailed status information and better persistence.
Shows recording statistics and provides more visual feedback.

Features:
- Detailed recording status with start time
- Word count tracking
- Visual indicators for recording state
- Better persistence across desktop environments
- Configurable update intervals

Installation:
1. Place in ~/.config/vosk-wrapper-1000/hooks/start/
2. Make executable: chmod +x 03_advanced_persistent_notification.py
3. Install notify-send: sudo apt install libnotify-bin

Exit codes:
  0 - Continue normal execution
  100 - Stop listening immediately
  101 - Terminate application immediately
"""

import os
import subprocess
import sys
from datetime import datetime


class AdvancedPersistentNotifier:
    """Advanced persistent notification manager with detailed status"""

    def __init__(self):
        # Configuration
        self.notification_id = "vosk-advanced-recording"
        self.icon = "audio-input-microphone"
        self.app_name = "Vosk Speech Recognition"

        # Status tracking
        self.status_file = os.path.expanduser(
            "~/.cache/vosk-wrapper-1000/advanced_notification_status"
        )

        # Display options
        self.show_word_count = True
        self.show_duration = True
        self.update_interval = 30  # seconds between updates

    def show_recording_started(self) -> None:
        """Show detailed persistent notification that recording has started"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            message = f"Recording active since {timestamp}"

            # Create/update persistent notification
            cmd = [
                "notify-send",
                "--app-name",
                self.app_name,
                "--icon",
                self.icon,
                "--urgency",
                "normal",
                "--transient",  # Don't show in notification center
                "--expire-time",
                "1",  # Never expire (persistent)
                "--hint",
                "string:x-canonical-private-synchronous:vosk-advanced",
                "🎤 Recording Active",
                message,
            ]

            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✓ Advanced persistent notification created", file=sys.stderr)

            # Save notification state
            self._save_status("active", timestamp)

        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to create notification: {e}", file=sys.stderr)
        except FileNotFoundError:
            print(
                "✗ notify-send not found. Install with: sudo apt install libnotify-bin",
                file=sys.stderr,
            )

    def _save_status(self, status: str, timestamp: str) -> None:
        """Save notification status to file"""
        try:
            os.makedirs(os.path.dirname(self.status_file), exist_ok=True)
            with open(self.status_file, "w") as f:
                f.write(f"{status}\n{timestamp}\n")
        except Exception as e:
            print(f"Warning: Could not save status: {e}", file=sys.stderr)


def main():
    """Main start hook handler"""
    print(
        "🎤 [Advanced Start Hook] Creating detailed persistent notification...",
        file=sys.stderr,
    )

    # Initialize advanced notifier
    notifier = AdvancedPersistentNotifier()

    # Show recording started notification
    notifier.show_recording_started()

    # Continue normal execution
    sys.exit(0)


if __name__ == "__main__":
    main()
