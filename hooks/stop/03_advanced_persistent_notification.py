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

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class AdvancedPersistentNotifier:
    """Advanced persistent notification manager with detailed status"""

    def __init__(self):
        # Configuration - must match start hook
        self.notification_id = "vosk-advanced-recording"
        self.icon = "audio-input-microphone"
        self.app_name = "Vosk Speech Recognition"

        # Status tracking
        self.status_file = os.path.expanduser(
            "~/.cache/vosk-wrapper-1000/advanced_notification_status.json"
        )

    def show_recording_stopped(self) -> None:
        """Update persistent notification with final recording statistics"""
        try:
            # Read status from start hook
            status_data = self._read_status()

            if not status_data or status_data.get("status") != "active":
                print("⚠️ No active recording status found", file=sys.stderr)
                return

            # Calculate final statistics
            start_time = self._parse_timestamp(status_data.get("start_time"))
            end_time = datetime.now()

            duration = end_time - start_time if start_time else None
            word_count = status_data.get("word_count", 0)

            # Build final notification
            title = "⏹️ Recording Complete"
            message = self._build_final_message(
                duration, word_count, start_time, end_time
            )

            cmd = self._build_notify_command(title, message, persistent=False)

            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(
                "✓ Advanced notification updated: Recording Complete", file=sys.stderr
            )

            # Clean up status file
            self._cleanup_status()

        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to update notification: {e}", file=sys.stderr)
        except FileNotFoundError:
            print(
                "✗ notify-send not found. Install with: sudo apt install libnotify-bin",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"✗ Unexpected error: {e}", file=sys.stderr)

    def _build_final_message(
        self,
        duration: Optional[timedelta],
        word_count: int,
        start_time: Optional[datetime],
        end_time: datetime,
    ) -> str:
        """Build the final notification message with statistics"""
        lines = []

        # Duration
        if duration:
            duration_str = str(duration).split(".")[0]  # Remove microseconds
            lines.append(f"Duration: {duration_str}")

        # Word count
        if word_count > 0:
            lines.append(f"Words transcribed: {word_count}")

        # Time range
        if start_time:
            start_str = start_time.strftime("%H:%M:%S")
            end_str = end_time.strftime("%H:%M:%S")
            lines.append(f"Time: {start_str} - {end_str}")

        # Words per minute calculation
        if duration and word_count > 0:
            minutes = duration.total_seconds() / 60
            if minutes > 0:
                wpm = word_count / minutes
                lines.append(f"Speed: {wpm:.1f} WPM")

        return "\n".join(lines)

    def _build_notify_command(
        self, title: str, message: str, persistent: bool = False
    ) -> list:
        """Build notify-send command with appropriate options"""
        cmd = [
            "notify-send",
            "--app-name",
            self.app_name,
            "--icon",
            self.icon,
            "--urgency",
            "normal",
            "--transient",  # Don't show in notification center
        ]

        if persistent:
            cmd.extend(["--expire-time", "0"])
            cmd.extend(
                ["--hint", "string:x-canonical-private-synchronous:vosk-advanced"]
            )
        else:
            cmd.extend(["--expire-time", "5000"])  # Show longer for completion
            cmd.extend(
                ["--hint", "string:x-canonical-private-synchronous:vosk-advanced"]
            )

        cmd.extend([title, message])
        return cmd

    def _read_status(self) -> Dict[str, Any]:
        """Read notification status from JSON file"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file) as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not read status: {e}", file=sys.stderr)
        return {}

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO timestamp string to datetime object"""
        if not timestamp_str:
            return None
        try:
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError):
            return None

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
