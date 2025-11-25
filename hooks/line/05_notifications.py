#!/usr/bin/env python3
"""
Notification Hook - Python script for desktop notifications during recording

This hook sends desktop notifications for each transcribed line while recording
is active. Perfect for getting real-time feedback during speech recognition.

Features:
- Desktop notifications with transcribed text
- Configurable notification settings
- Sound alerts (optional)
- Automatic filtering of short/empty text

Installation:
1. Place in ~/.config/vosk-wrapper-1000/hooks/line/
2. Make executable: chmod +x 05_notifications.py
3. Ensure notify-send is installed (libnotify-tools package)

Arguments:
  $1 - Current transcribed line text
  stdin - Full transcript context so far

Exit codes:
  0 - Continue processing normally
"""

import subprocess
import sys
import os
from datetime import datetime


class DesktopNotifier:
    """Simple desktop notification manager"""

    def __init__(self):
        self.icon = "audio-input-microphone"
        self.timeout = 3000  # 3 seconds
        self.sound_enabled = True
        self.sound_file = "/usr/share/sounds/freedesktop/stereo/message.oga"

    def send_notification(self, title: str, message: str, urgency: str = "normal"):
        """Send desktop notification using notify-send"""
        try:
            cmd = [
                "notify-send",
                "--icon",
                self.icon,
                "--urgency",
                urgency,
                "--expire-time",
                str(self.timeout),
                title,
                message,
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"✓ Desktop notification: {title}", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to send notification: {e}", file=sys.stderr)
        except FileNotFoundError:
            print(
                "✗ notify-send not found. Install with: sudo apt install libnotify-bin",
                file=sys.stderr,
            )

    def play_sound(self):
        """Play notification sound"""
        if not self.sound_enabled:
            return

        if not os.path.exists(self.sound_file):
            print(f"✗ Sound file not found: {self.sound_file}", file=sys.stderr)
            return

        try:
            # Try different audio players
            for player in ["paplay", "aplay", "play"]:
                try:
                    subprocess.run(
                        [player, self.sound_file],
                        check=True,
                        capture_output=True,
                        timeout=2,
                    )
                    print("✓ Sound notification played", file=sys.stderr)
                    return
                except (
                    subprocess.CalledProcessError,
                    subprocess.TimeoutExpired,
                    FileNotFoundError,
                ):
                    continue
            print("✗ No audio player found", file=sys.stderr)
        except Exception as e:
            print(f"✗ Sound error: {e}", file=sys.stderr)


def main():
    """Main notification handler"""
    if len(sys.argv) < 2:
        print("Usage: 05_notifications.py <transcribed_text>", file=sys.stderr)
        sys.exit(1)

    current_line = sys.argv[1].strip()

    # Skip very short transcriptions
    if len(current_line) < 2:
        print(f"⏭️ Skipping short text: '{current_line}'", file=sys.stderr)
        sys.exit(0)

    # Read full context from stdin if available
    context = None
    if not sys.stdin.isatty():
        context = sys.stdin.read().strip()

    # Initialize notifier
    notifier = DesktopNotifier()

    # Create notification content
    title = "🎤 Speech Detected"
    message = current_line

    # Add context info if available
    if context and len(context) > len(current_line):
        total_words = len(context.split())
        message += f"\n({total_words} words total)"

    # Send notification
    notifier.send_notification(title, message)

    # Play sound for important phrases
    important_keywords = ["help", "stop", "shutdown", "emergency"]
    if any(keyword in current_line.lower() for keyword in important_keywords):
        notifier.play_sound()

    # Log activity
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"📢 [{timestamp}] Notified: '{current_line}'", file=sys.stderr)

    # Continue processing normally
    sys.exit(0)


if __name__ == "__main__":
    main()
