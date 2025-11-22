#!/usr/bin/env python3
"""
Example script demonstrating webhook integration
This can be called from the trigger word detector or used as a template
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from typing import Optional


def send_slack_notification(webhook_url: str, message: str, text: str):
    """
    Send a notification to Slack

    Args:
        webhook_url: Slack webhook URL
        message: Message to send
        text: The transcribed text that triggered this
    """
    payload = {
        "text": message,
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Trigger Detected*\n{message}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Transcribed Text:*\n{text}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{datetime.now().isoformat()}",
                    },
                ],
            },
        ],
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=data, headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"Slack notification sent: {response.status}", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"Error sending Slack notification: {e}", file=sys.stderr)


def send_discord_notification(webhook_url: str, message: str, text: str):
    """
    Send a notification to Discord

    Args:
        webhook_url: Discord webhook URL
        message: Message to send
        text: The transcribed text that triggered this
    """
    payload = {
        "content": message,
        "embeds": [
            {
                "title": "Trigger Word Detected",
                "description": text,
                "color": 15158332,  # Red color
                "timestamp": datetime.now().isoformat(),
            }
        ],
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=data, headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"Discord notification sent: {response.status}", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"Error sending Discord notification: {e}", file=sys.stderr)


def send_generic_webhook(
    webhook_url: str, trigger_name: str, text: str, context: Optional[str] = None
):
    """
    Send a generic webhook with trigger information

    Args:
        webhook_url: Webhook URL
        trigger_name: Name of the trigger
        text: Current line text
        context: Full transcript context
    """
    payload = {
        "trigger": trigger_name,
        "text": text,
        "context": context,
        "timestamp": datetime.now().isoformat(),
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=data, headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"Webhook sent successfully: {response.status}", file=sys.stderr)
            return True
    except urllib.error.URLError as e:
        print(f"Error sending webhook: {e}", file=sys.stderr)
        return False


def main():
    """Example usage as a standalone script"""
    if len(sys.argv) < 2:
        print("Usage: webhook_example.py <text>", file=sys.stderr)
        sys.exit(1)

    text = sys.argv[1]
    context = sys.stdin.read() if not sys.stdin.isatty() else None

    # Example: Send to a generic webhook
    webhook_url = "https://hooks.example.com/trigger"
    send_generic_webhook(webhook_url, "test_trigger", text, context)

    # Example: Send to Slack (uncomment and add your webhook URL)
    # slack_webhook = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    # send_slack_notification(slack_webhook, "Alert: Trigger detected", text)

    # Example: Send to Discord (uncomment and add your webhook URL)
    # discord_webhook = "https://discord.com/api/webhooks/YOUR/WEBHOOK/URL"
    # send_discord_notification(discord_webhook, "Alert: Trigger detected", text)


if __name__ == "__main__":
    main()
