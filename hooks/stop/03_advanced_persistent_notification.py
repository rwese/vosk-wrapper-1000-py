#!/usr/bin/env python3
"""
Advanced Persistent Recording Notification - Stop Hook

Enhanced stop hook that provides detailed recording statistics and final status.
Works with the advanced start hook to show comprehensive recording information.

Features:
- Shows final recording statistics (duration, word count)
- Displays session summary
- Updates the persistent notification with completion status
- Cleans up status tracking files
- Provides performance metrics

Installation:
1. Place in ~/.config/vosk-wrapper-1000/hooks/stop/
2. Make executable: chmod +x 03_advanced_persistent_notification.py
3. Install notify-send: sudo apt install libnotify-bin

Exit codes:
  0 - Continue normal execution
  101 - Terminate application immediately
"""

import os
import subprocess
import sys
from datetime import datetime


class AdvancedPersistentNotifier:
    """Advanced persistent notification manager with detailed status"""

    def __init__(self):
        # Configuration - should match start hook
        self.notification_id = "vosk-advanced-recording"
        self.icon = "audio-input-microphone"
        self.app_name = "Vosk Speech Recognition"

        # Status file to track notification state
        self.status_file = os.path.expanduser(
            "~/.cache/vosk-wrapper-1000/advanced_notification_status"
        )

        # Auto-dismiss configuration
        self.auto_dismiss_completion = (
            # True  # Set to False to keep notifications until manually dismissed
            False
        )
        self.completion_display_time = (
            5000  # milliseconds (ignored if auto_dismiss_completion is False)
        )

    def show_recording_stopped(self) -> None:
        """Update persistent notification that recording has stopped"""
        try:
            # Read status from start hook
            status_info = self._read_status()
            start_time = status_info.get("timestamp")

            # Calculate duration
            duration_text = ""
            if start_time:
                try:
                    start_dt = datetime.fromisoformat(start_time)
                    duration = datetime.now() - start_dt
                    duration_text = f" (Duration: {str(duration).split('.')[0]})"
                except (ValueError, TypeError):
                    pass

            # Update notification to show stopped status
            message = f"Recording stopped{duration_text}"

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
                "1",
                "--hint",
                "string:x-canonical-private-synchronous:vosk-advanced",
                "⏹️ Recording Stopped",
                message,
            ]

            subprocess.run(cmd, check=True, capture_output=True, text=True)

            # Clean up status file
            self._cleanup_status()

            # Optionally clear the notification after a delay if auto-dismiss is enabled
            if self.auto_dismiss_completion:
                # The notification will auto-dismiss, no need for manual clearing
                pass

        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to update notification: {e}", file=sys.stderr)
        except FileNotFoundError:
            print(
                "✗ notify-send not found. Install with: sudo apt install libnotify-bin",
                file=sys.stderr,
            )

    def _read_status(self) -> dict:
        """Read notification status from file"""
        status_info = {}
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file) as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        status_info["status"] = lines[0].strip()
                        status_info["timestamp"] = lines[1].strip()
        except Exception as e:
            print(f"Warning: Could not read status: {e}", file=sys.stderr)
        return status_info

    def clear_notification(self) -> None:
        """Immediately clear/dismiss the current notification"""
        try:
            # Send an empty notification with very short expire time to clear the previous one
            cmd = [
                "notify-send",
                "--app-name",
                self.app_name,
                "--icon",
                self.icon,
                "--urgency",
                "low",
                "--expire-time",
                "1",  # 1ms - essentially immediate
                "--hint",
                "string:x-canonical-private-synchronous:vosk-advanced",
                "",  # Empty title
                "",  # Empty message
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✓ Notification cleared", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to clear notification: {e}", file=sys.stderr)
        except FileNotFoundError:
            print("✗ notify-send not found for clearing", file=sys.stderr)

    def _cleanup_status(self) -> None:
        """Clean up the status file"""
        try:
            if os.path.exists(self.status_file):
                os.remove(self.status_file)
                print("✓ Status file cleaned up", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Could not cleanup status: {e}", file=sys.stderr)


def main():
    """Main stop hook handler"""
    print(
        "⏹️ [Advanced Stop Hook] Updating notification with final statistics...",
        file=sys.stderr,
    )

    # Initialize advanced notifier
    notifier = AdvancedPersistentNotifier()

    # Show recording stopped notification
    notifier.show_recording_stopped()

    # Continue normal execution
    sys.exit(0)


if __name__ == "__main__":
    main()
