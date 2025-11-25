#!/usr/bin/env python3
"""
Advanced Notification Hook - Multiple notification methods for speech recognition

This comprehensive notification hook demonstrates various ways to get notified
during active recording sessions. It supports desktop notifications, webhooks,
and custom actions.

Features:
- Desktop notifications with urgency levels
- Webhook support (Slack, Discord, generic HTTP)
- Sound alerts with different audio players
- Configurable filtering and thresholds
- Error handling and fallbacks
- Performance optimized for real-time use

Installation:
1. Place in ~/.config/vosk-wrapper-1000/hooks/line/
2. Make executable: chmod +x 06_advanced_notifications.py
3. Configure webhook URLs and settings below
4. Install dependencies: sudo apt install libnotify-bin sox (for sound)

Arguments:
  $1 - Current transcribed line text
  stdin - Full transcript context so far

Exit codes:
  0 - Continue processing normally
  100 - Stop listening (for urgent keywords)
"""

import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Optional, Dict, Any


class NotificationConfig:
    """Configuration for notification settings"""

    def __init__(self):
        # Desktop notification settings
        self.desktop_enabled = True
        self.desktop_icon = "audio-input-microphone"
        self.desktop_timeout = 3000  # milliseconds

        # Webhook settings
        self.webhook_enabled = False
        self.webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
        self.webhook_service = "slack"  # slack, discord, generic

        # Sound settings
        self.sound_enabled = True
        self.sound_file = "/usr/share/sounds/freedesktop/stereo/message.oga"

        # Filtering settings
        self.min_length = 2  # Minimum text length to notify
        self.urgent_keywords = ["help", "emergency", "stop", "shutdown", "abort"]
        self.quiet_keywords = ["um", "uh", "like", "you know"]  # Skip these

        # Performance settings
        self.async_webhooks = True  # Send webhooks in background
        self.webhook_timeout = 3  # seconds


class AdvancedNotifier:
    """Advanced notification manager with multiple methods"""

    def __init__(self, config: NotificationConfig):
        self.config = config
        self.webhook_thread: Optional[threading.Thread] = None

    def notify(self, text: str, context: Optional[str] = None) -> None:
        """Send notifications using all enabled methods"""
        # Filter text
        if not self._should_notify(text):
            return

        # Send desktop notification
        if self.config.desktop_enabled:
            self._send_desktop_notification(text, context)

        # Send webhook (async or sync)
        if self.config.webhook_enabled:
            if self.config.async_webhooks:
                self._send_webhook_async(text, context)
            else:
                self._send_webhook_sync(text, context)

        # Play sound for urgent messages
        if self.config.sound_enabled and self._is_urgent(text):
            self._play_sound()

    def _should_notify(self, text: str) -> bool:
        """Determine if we should send a notification for this text"""
        text = text.strip().lower()

        # Check minimum length
        if len(text) < self.config.min_length:
            return False

        # Skip quiet keywords
        if any(keyword in text for keyword in self.config.quiet_keywords):
            print(f"⏭️ Skipping quiet keyword: '{text}'", file=sys.stderr)
            return False

        return True

    def _is_urgent(self, text: str) -> bool:
        """Check if text contains urgent keywords"""
        text = text.lower()
        return any(keyword in text for keyword in self.config.urgent_keywords)

    def _send_desktop_notification(self, text: str, context: Optional[str]) -> None:
        """Send desktop notification"""
        try:
            urgency = "critical" if self._is_urgent(text) else "normal"
            title = "🚨 URGENT" if urgency == "critical" else "🎤 Speech"

            message = text
            if context and len(context) > len(text):
                total_words = len(context.split())
                message += f" ({total_words} words)"

            cmd = [
                "notify-send",
                "--icon",
                self.config.desktop_icon,
                "--urgency",
                urgency,
                "--expire-time",
                str(self.config.desktop_timeout),
                title,
                message,
            ]

            subprocess.run(cmd, check=True, capture_output=True, timeout=1)
            print(f"✓ Desktop notification sent", file=sys.stderr)

        except subprocess.TimeoutExpired:
            print("✗ Desktop notification timeout", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"✗ Desktop notification failed: {e}", file=sys.stderr)
        except FileNotFoundError:
            print("✗ notify-send not found", file=sys.stderr)

    def _send_webhook_async(self, text: str, context: Optional[str]) -> None:
        """Send webhook in background thread"""
        if self.webhook_thread and self.webhook_thread.is_alive():
            print("⚠️ Webhook thread busy, skipping", file=sys.stderr)
            return

        self.webhook_thread = threading.Thread(
            target=self._send_webhook_sync, args=(text, context), daemon=True
        )
        self.webhook_thread.start()

    def _send_webhook_sync(self, text: str, context: Optional[str]) -> None:
        """Send webhook synchronously"""
        try:
            payload = self._build_webhook_payload(text, context)
            data = json.dumps(payload).encode("utf-8")

            req = urllib.request.Request(
                self.config.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )

            with urllib.request.urlopen(
                req, timeout=self.config.webhook_timeout
            ) as response:
                print(f"✓ Webhook sent ({response.status})", file=sys.stderr)

        except urllib.error.URLError as e:
            print(f"✗ Webhook failed: {e}", file=sys.stderr)
        except Exception as e:
            print(f"✗ Webhook error: {e}", file=sys.stderr)

    def _build_webhook_payload(
        self, text: str, context: Optional[str]
    ) -> Dict[str, Any]:
        """Build webhook payload based on service type"""
        base_payload = {
            "text": text,
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "urgent": self._is_urgent(text),
            "source": "vosk-wrapper-advanced-notification",
        }

        if self.config.webhook_service == "slack":
            return {
                "text": f"🎤 {'🚨 URGENT: ' if base_payload['urgent'] else ''}Speech Detected",
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Speech Detected*"},
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Text:*\n{text}"},
                            {
                                "type": "mrkdwn",
                                "text": f"*Time:*\n{datetime.now().strftime('%H:%M:%S')}",
                            },
                        ],
                    },
                ],
            }

        elif self.config.webhook_service == "discord":
            embed = {
                "title": "🎤 Speech Detected"
                + (" 🚨" if base_payload["urgent"] else ""),
                "description": text,
                "color": 15158332 if base_payload["urgent"] else 3447003,
                "timestamp": base_payload["timestamp"],
                "footer": {"text": "Vosk Speech Recognition"},
            }

            if context:
                embed["fields"] = [
                    {
                        "name": "Full Context",
                        "value": context[:1000]
                        + ("..." if len(context) > 1000 else ""),
                        "inline": False,
                    }
                ]

            return {"embeds": [embed]}

        else:  # generic
            return base_payload

    def _play_sound(self) -> None:
        """Play notification sound"""
        if not self.config.sound_enabled:
            return

        try:
            # Try different audio players in order of preference
            players = [
                ["paplay", self.config.sound_file],  # PulseAudio
                ["aplay", self.config.sound_file],  # ALSA
                ["play", self.config.sound_file],  # SoX
                ["mpg123", "-q", self.config.sound_file],  # MP3
            ]

            for cmd in players:
                try:
                    subprocess.run(cmd, check=True, capture_output=True, timeout=2)
                    print("✓ Sound notification played", file=sys.stderr)
                    return
                except (
                    subprocess.CalledProcessError,
                    subprocess.TimeoutExpired,
                    FileNotFoundError,
                ):
                    continue

            print("✗ No suitable audio player found", file=sys.stderr)

        except Exception as e:
            print(f"✗ Sound error: {e}", file=sys.stderr)


def main():
    """Main notification handler"""
    if len(sys.argv) < 2:
        print("Usage: 06_advanced_notifications.py <transcribed_text>", file=sys.stderr)
        sys.exit(1)

    current_line = sys.argv[1].strip()

    # Read full context from stdin if available
    context = None
    if not sys.stdin.isatty():
        context = sys.stdin.read().strip()

    # Initialize configuration and notifier
    config = NotificationConfig()
    notifier = AdvancedNotifier(config)

    # Send notifications
    start_time = time.time()
    notifier.notify(current_line, context)
    elapsed = time.time() - start_time

    # Log performance
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(
        f"📢 [{timestamp}] Processed: '{current_line[:50]}' ({elapsed:.2f}s)",
        file=sys.stderr,
    )

    # Exit with special code for urgent keywords
    if config.urgent_keywords and any(
        kw in current_line.lower() for kw in config.urgent_keywords
    ):
        print("🚨 Urgent keyword detected, stopping listening", file=sys.stderr)
        sys.exit(100)  # Stop listening

    # Continue normally
    sys.exit(0)


if __name__ == "__main__":
    main()
