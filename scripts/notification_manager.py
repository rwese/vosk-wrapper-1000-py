#!/usr/bin/env python3
"""
Notification Manager - Control and manage vosk-wrapper-1000 notifications

This utility script helps manage notifications created by the persistent
notification hooks. It can clear stuck notifications, check notification
status, and provide notification management tools.

Usage:
    python notification_manager.py <command> [options]

Commands:
    clear           - Clear all vosk-wrapper-1000 notifications
    status          - Show current notification status
    test            - Send a test notification
    list            - List active notifications (if supported)
    config          - Show notification configuration

Examples:
    python notification_manager.py clear
    python notification_manager.py status
    python notification_manager.py test
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict


class NotificationManager:
    """Manages vosk-wrapper-1000 notifications"""

    def __init__(self):
        self.app_name = "Vosk Speech Recognition"
        self.icon = "audio-input-microphone"
        self.status_file = os.path.expanduser(
            "~/.cache/vosk-wrapper-1000/notification_status"
        )
        self.advanced_status_file = os.path.expanduser(
            "~/.cache/vosk-wrapper-1000/advanced_notification_status.json"
        )

    def clear_notifications(self) -> None:
        """Clear all vosk-wrapper-1000 notifications"""
        print("🧹 Clearing vosk-wrapper-1000 notifications...")

        # Clear basic notification
        self._clear_notification("vosk-recording-status")

        # Clear advanced notification
        self._clear_notification("vosk-advanced-recording")

        # Clean up status files
        self._cleanup_status_files()

        print("✅ All notifications cleared")

    def _clear_notification(self, notification_id: str) -> None:
        """Clear a specific notification by sending an empty replacement"""
        try:
            cmd = [
                "notify-send",
                "--app-name",
                self.app_name,
                "--icon",
                self.icon,
                "--urgency",
                "low",
                "--transient",
                "--expire-time",
                "1",  # 1ms - essentially immediate
                "--hint",
                f"string:x-canonical-private-synchronous:{notification_id}",
                "",  # Empty title
                "",  # Empty message
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to clear notification {notification_id}: {e}")
        except FileNotFoundError:
            print(
                "❌ notify-send not found. Install with: sudo apt install libnotify-bin"
            )

    def show_status(self) -> None:
        """Show current notification status"""
        print("📊 Vosk Notification Status")
        print("=" * 40)

        # Check status files
        basic_status = self._read_basic_status()
        advanced_status = self._read_advanced_status()

        if basic_status:
            print(f"🎤 Basic Notification: {basic_status.get('status', 'unknown')}")
            if basic_status.get("timestamp"):
                try:
                    dt = datetime.fromisoformat(basic_status["timestamp"])
                    print(f"   Started: {dt.strftime('%H:%M:%S')}")
                except (ValueError, TypeError):
                    print(f"   Timestamp: {basic_status['timestamp']}")
        else:
            print("🎤 Basic Notification: No active status")

        if advanced_status:
            print(
                f"📈 Advanced Notification: {advanced_status.get('status', 'unknown')}"
            )
            if advanced_status.get("start_time"):
                try:
                    dt = datetime.fromisoformat(advanced_status["start_time"])
                    duration = datetime.now() - dt
                    print(
                        f"   Started: {dt.strftime('%H:%M:%S')} ({str(duration).split('.')[0]} ago)"
                    )
                    print(f"   Words: {advanced_status.get('word_count', 0)}")
                except (ValueError, TypeError):
                    print(f"   Start time: {advanced_status['start_time']}")
        else:
            print("📈 Advanced Notification: No active status")

        # Check if notify-send is available
        try:
            result = subprocess.run(
                ["which", "notify-send"], capture_output=True, text=True
            )
            if result.returncode == 0:
                print("✅ Notification system: Available")
            else:
                print("❌ Notification system: Not found")
        except (OSError, subprocess.SubprocessError):
            print("❌ Notification system: Error checking")

    def send_test_notification(self) -> None:
        """Send a test notification"""
        print("🧪 Sending test notification...")

        try:
            cmd = [
                "notify-send",
                "--app-name",
                self.app_name,
                "--icon",
                self.icon,
                "--urgency",
                "normal",
                "--transient",
                "--expire-time",
                "3000",
                "🧪 Test Notification",
                f"Vosk notifications are working!\nTime: {datetime.now().strftime('%H:%M:%S')}",
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✅ Test notification sent successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to send test notification: {e}")
        except FileNotFoundError:
            print(
                "❌ notify-send not found. Install with: sudo apt install libnotify-bin"
            )

    def list_notifications(self) -> None:
        """Attempt to list active notifications (limited support)"""
        print("📋 Active Notifications")
        print("=" * 30)

        # Try different tools to list notifications
        tools = [
            (
                [
                    "dbus-send",
                    "--session",
                    "--dest=org.freedesktop.Notifications",
                    "--type=method_call",
                    "/org/freedesktop/Notifications",
                    "org.freedesktop.Notifications.GetCapabilities",
                ],
                "D-Bus direct",
            ),
            (["dunstctl", "history"], "Dunst history"),
            (["dunstctl", "count"], "Dunst count"),
        ]

        success = False
        for cmd, name in tools:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    print(f"✅ {name}:")
                    print(result.stdout)
                    success = True
                    break
            except (
                subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
                FileNotFoundError,
            ):
                continue

        if not success:
            print("i Unable to list notifications automatically")
            print("   Try: dunstctl history (if using Dunst)")
            print("   Try: notify-send --help (to verify installation)")

    def show_config(self) -> None:
        """Show notification configuration"""
        print("⚙️  Notification Configuration")
        print("=" * 35)

        config_items = [
            ("App Name", self.app_name),
            ("Icon", self.icon),
            ("Status File", self.status_file),
            ("Advanced Status File", self.advanced_status_file),
            ("Transient", "Yes (doesn't clutter notification center)"),
            ("Auto-dismiss", "Yes (completion notifications auto-dismiss)"),
        ]

        for key, value in config_items:
            print(f"{key:20}: {value}")

        print("\n📁 Status Files:")
        for status_file in [self.status_file, self.advanced_status_file]:
            if os.path.exists(status_file):
                try:
                    size = os.path.getsize(status_file)
                    mtime = datetime.fromtimestamp(os.path.getmtime(status_file))
                    print(f"  ✅ {status_file}")
                    print(
                        f"     Size: {size} bytes, Modified: {mtime.strftime('%H:%M:%S')}"
                    )
                except OSError:
                    print(f"  ✅ {status_file} (exists)")
            else:
                print(f"  ❌ {status_file} (not found)")

    def _read_basic_status(self) -> Dict[str, str]:
        """Read basic notification status"""
        status = {}
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file) as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        status["status"] = lines[0].strip()
                        status["timestamp"] = lines[1].strip()
        except Exception as e:
            print(f"Warning: Could not read basic status: {e}")
        return status

    def _read_advanced_status(self) -> Dict[str, Any]:
        """Read advanced notification status"""
        try:
            if os.path.exists(self.advanced_status_file):
                with open(self.advanced_status_file) as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not read advanced status: {e}")
        return {}

    def _cleanup_status_files(self) -> None:
        """Clean up status files"""
        for status_file in [self.status_file, self.advanced_status_file]:
            try:
                if os.path.exists(status_file):
                    os.remove(status_file)
                    print(f"🗑️  Cleaned up: {status_file}")
            except Exception as e:
                print(f"Warning: Could not cleanup {status_file}: {e}")


def main():
    """Main notification manager"""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()
    manager = NotificationManager()

    commands = {
        "clear": manager.clear_notifications,
        "status": manager.show_status,
        "test": manager.send_test_notification,
        "list": manager.list_notifications,
        "config": manager.show_config,
    }

    if command in commands:
        try:
            commands[command]()
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands:", ", ".join(commands.keys()))
        sys.exit(1)


if __name__ == "__main__":
    main()
