#!/usr/bin/env python3
"""
Webhook Notification Hook - Send transcribed speech to external services

This hook sends notifications to webhooks (Slack, Discord, etc.) for each
transcribed line during recording. Perfect for remote monitoring or integration
with other systems.

Features:
- Support for Slack, Discord, and generic webhooks
- Asynchronous sending (non-blocking)
- Configurable filtering
- Error handling with retries
- JSON payload with full context

Installation:
1. Place in ~/.config/vosk-wrapper-1000/hooks/line/
2. Make executable: chmod +x 07_webhook_notifications.py
3. Edit the webhook URLs and settings below

Arguments:
  $1 - Current transcribed line text
  stdin - Full transcript context so far

Exit codes:
  0 - Continue processing normally
"""

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, Optional


class WebhookNotifier:
    """Webhook notification manager"""

    def __init__(self):
        # Configuration - EDIT THESE VALUES
        self.enabled = True
        self.service = "slack"  # "slack", "discord", or "generic"
        self.webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

        # Filtering options
        self.min_length = 3  # Minimum text length
        self.skip_keywords = ["um", "uh", "like"]  # Skip these words

        # Performance options
        self.timeout = 5  # seconds
        self.max_retries = 2
        self.async_send = True

    def should_notify(self, text: str) -> bool:
        """Check if we should send a notification"""
        if not self.enabled:
            return False

        text = text.strip().lower()

        # Check minimum length
        if len(text) < self.min_length:
            return False

        # Skip certain keywords
        if any(keyword in text for keyword in self.skip_keywords):
            return False

        return True

    def send_notification(self, text: str, context: Optional[str] = None) -> None:
        """Send webhook notification"""
        if not self.should_notify(text):
            return

        if self.async_send:
            # Send in background thread
            thread = threading.Thread(
                target=self._send_webhook, args=(text, context), daemon=True
            )
            thread.start()
        else:
            # Send synchronously
            self._send_webhook(text, context)

    def _send_webhook(self, text: str, context: Optional[str]) -> None:
        """Send the actual webhook request"""
        payload = self._build_payload(text, context)

        for attempt in range(self.max_retries + 1):
            try:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    self.webhook_url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                )

                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    print(f"✓ Webhook sent ({response.status})", file=sys.stderr)
                    return

            except urllib.error.HTTPError as e:
                print(
                    f"✗ Webhook HTTP error (attempt {attempt + 1}): {e.code}",
                    file=sys.stderr,
                )
            except urllib.error.URLError as e:
                print(
                    f"✗ Webhook network error (attempt {attempt + 1}): {e}",
                    file=sys.stderr,
                )
            except Exception as e:
                print(f"✗ Webhook error (attempt {attempt + 1}): {e}", file=sys.stderr)

            if attempt < self.max_retries:
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff

        print("✗ Webhook failed after all retries", file=sys.stderr)

    def _build_payload(self, text: str, context: Optional[str]) -> Dict[str, Any]:
        """Build the webhook payload based on service type"""
        timestamp = datetime.now().isoformat()

        if self.service == "slack":
            return {
                "text": "🎤 Speech Detected",
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "*New Speech Detected*"},
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

        elif self.service == "discord":
            embed = {
                "title": "🎤 Speech Detected",
                "description": text,
                "color": 3447003,  # Blue
                "timestamp": timestamp,
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

        else:  # generic webhook
            return {
                "event": "speech_detected",
                "text": text,
                "context": context,
                "timestamp": timestamp,
                "word_count": len(text.split()) if text else 0,
                "source": "vosk-wrapper-webhook-hook",
            }


def main():
    """Main webhook handler"""
    if len(sys.argv) < 2:
        print("Usage: 07_webhook_notifications.py <transcribed_text>", file=sys.stderr)
        sys.exit(1)

    current_line = sys.argv[1].strip()

    # Read full context from stdin if available
    context = None
    if not sys.stdin.isatty():
        context = sys.stdin.read().strip()

    # Initialize notifier
    notifier = WebhookNotifier()

    # Send notification
    start_time = time.time()
    notifier.send_notification(current_line, context)
    elapsed = time.time() - start_time

    # Log activity
    timestamp = datetime.now().strftime("%H:%M:%S")
    if notifier.should_notify(current_line):
        print(
            f"🌐 [{timestamp}] Webhook sent: '{current_line[:50]}' ({elapsed:.2f}s)",
            file=sys.stderr,
        )
    else:
        print(f"⏭️ [{timestamp}] Skipped: '{current_line}'", file=sys.stderr)

    # Continue processing normally
    sys.exit(0)


if __name__ == "__main__":
    main()
