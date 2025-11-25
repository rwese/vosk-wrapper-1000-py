#!/usr/bin/env python3
"""
Persistent Recording Notification - Stop Hook

This hook updates or dismisses the persistent notification when recording stops.
It works with the start hook to provide continuous recording status feedback.

Features:
- Updates the persistent notification when recording stops
- Shows recording duration and final status
- Can dismiss the notification or show completion message
- Reads status from the start hook for accurate timing

Installation:
1. Place in ~/.config/vosk-wrapper-1000/hooks/stop/
2. Make executable: chmod +x 02_persistent_notification.py
3. Install notify-send: sudo apt install libnotify-bin

Exit codes:
  0 - Continue normal execution
  101 - Terminate application immediately
"""

import os
import subprocess
import sys
from datetime import datetime


class PersistentNotifier:
    """Manages persistent recording notifications"""

    def __init__(self):
        # Configuration - should match start hook
        self.notification_id = "vosk-recording-status"
        self.icon = "audio-input-microphone"
        self.app_name = "Vosk Speech Recognition"

        # Status file to track notification state
        self.status_file = os.path.expanduser(
            "~/.cache/vosk-wrapper-1000/notification_status"
        )

        # Auto-dismiss configuration
        self.auto_dismiss_completion = (
            True  # Set to False to keep notifications until manually dismissed
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
                "low",
                "--transient",  # Don't show in notification center
                "--expire-time",
                "1",  # 1ms - essentially immediate
                "--hint",
                "string:x-canonical-private-synchronous:vosk-recording",
                "",  # Empty title
                "",  # Empty message
            ]

            if self.auto_dismiss_completion:
                cmd.extend(["--expire-time", str(self.completion_display_time)])
            else:
                cmd.extend(["--expire-time", "0"])  # Never auto-dismiss

            cmd.extend(
                [
                    "--hint",
                    "string:x-canonical-private-synchronous:vosk-recording",
                    "⏹️ Recording Stopped",
                    message,
                ]
            )

            subprocess.run(cmd, check=True, capture_output=True, text=True)
            dismiss_msg = (
                " (auto-dismiss in 5s)"
                if self.auto_dismiss_completion
                else " (manual dismiss)"
            )
            print(
                f"✓ Persistent notification updated: Recording Stopped{dismiss_msg}",
                file=sys.stderr,
            )

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
                "string:x-canonical-private-synchronous:vosk-recording",
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
        except Exception as e:
            print(f"Warning: Could not cleanup status: {e}", file=sys.stderr)


def main():
    """Main stop hook handler"""
    print(
        "⏹️ [Stop Hook] Updating persistent recording notification...", file=sys.stderr
    )

    # Initialize notifier
    notifier = PersistentNotifier()

    # Show recording stopped notification
    notifier.show_recording_stopped()

    # Continue normal execution
    sys.exit(0)


if __name__ == "__main__":
    main()
