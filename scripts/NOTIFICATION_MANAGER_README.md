# Notification Manager

A utility script to manage vosk-wrapper-1000 notifications. This tool helps you control, monitor, and troubleshoot the persistent notification system.

## Features

- **Clear Notifications**: Remove stuck or unwanted notifications
- **Status Monitoring**: Check current notification state and status files
- **Test Notifications**: Verify notification system is working
- **Configuration Display**: Show current notification settings
- **Status File Management**: Clean up notification status files

## Installation

```bash
# The script is already included in the vosk-wrapper-1000 project
ls scripts/notification_manager.py

# Make sure it's executable
chmod +x scripts/notification_manager.py
```

## Usage

### Basic Commands

```bash
# Show help
python scripts/notification_manager.py

# Check notification status
python scripts/notification_manager.py status

# Send a test notification
python scripts/notification_manager.py test

# Clear all vosk notifications
python scripts/notification_manager.py clear

# Show configuration
python scripts/notification_manager.py config
```

### Advanced Usage

```bash
# Check if notifications are working during recording
python scripts/notification_manager.py status

# Clear stuck notifications after a crash
python scripts/notification_manager.py clear

# Verify notification system before starting vosk
python scripts/notification_manager.py test
```

## Command Reference

### `status`
Shows current notification status including:
- Basic notification state (active/stopped)
- Advanced notification statistics (duration, word count)
- Status file information
- Notification system availability

### `test`
Sends a test notification to verify the system is working:
- Uses the same settings as vosk notifications
- Shows timestamp and confirmation
- Helps diagnose notification issues

### `clear`
Clears all vosk-wrapper-1000 notifications:
- Removes active notifications from system tray
- Cleans up status files
- Safe to run even when no notifications are active

### `config`
Displays notification configuration:
- App name and icon settings
- Status file locations
- Transient and auto-dismiss settings
- Status file existence and sizes

### `list`
Attempts to list active notifications:
- Tries multiple notification daemons (Dunst, etc.)
- Provides manual commands if automatic detection fails

## Troubleshooting

### Notifications Not Appearing
```bash
# Test basic notification system
python notification_manager.py test

# Check if notify-send is installed
which notify-send

# Verify notification daemon
systemctl --user status dunst  # or your notification daemon
```

### Stuck Notifications
```bash
# Clear all vosk notifications
python notification_manager.py clear

# Check status files are cleaned up
python notification_manager.py config
```

### Status Files Not Updating
```bash
# Check file permissions
ls -la ~/.cache/vosk-wrapper-1000/

# Clean up manually
rm ~/.cache/vosk-wrapper-1000/*notification_status*

# Check disk space
df -h ~/.cache/
```

## Integration with Vosk

### During Development
```bash
# Before starting vosk
python notification_manager.py test

# Check status during recording
python notification_manager.py status

# Clean up after testing
python notification_manager.py clear
```

### In Scripts/Automation
```bash
#!/bin/bash
# vosk-start.sh

# Verify notifications work
if ! python scripts/notification_manager.py test >/dev/null 2>&1; then
    echo "Warning: Notifications not working"
fi

# Start vosk
vosk-wrapper-1000 daemon
vosk-wrapper-1000 start

# Monitor status
python scripts/notification_manager.py status
```

## Status Files

The notification manager uses these status files:
- `~/.cache/vosk-wrapper-1000/notification_status` - Basic notification state
- `~/.cache/vosk-wrapper-1000/advanced_notification_status.json` - Advanced statistics

These files are automatically cleaned up when notifications are cleared or when recording sessions end normally.

## Security Notes

- Status files contain only session metadata (timestamps, word counts)
- No sensitive information is stored
- Files are created with user-only permissions
- Safe to delete manually if needed

## Examples

### Development Workflow
```bash
# 1. Test notifications
python scripts/notification_manager.py test

# 2. Start recording
vosk-wrapper-1000 daemon
vosk-wrapper-1000 start

# 3. Check status
python scripts/notification_manager.py status

# 4. Stop recording
vosk-wrapper-1000 stop

# 5. Clean up
python scripts/notification_manager.py clear
```

### Monitoring Script
```bash
#!/bin/bash
# monitor-notifications.sh

while true; do
    echo "=== $(date) ==="
    python scripts/notification_manager.py status
    sleep 30
done
```

## Dependencies

- **notify-send**: For desktop notifications (libnotify-bin package)
- **Python 3.6+**: For the management script
- **Notification daemon**: Dunst, GNOME notifications, etc.

## Error Handling

The script handles common errors gracefully:
- Missing notification system
- Permission issues
- Corrupted status files
- Network issues (for future webhook features)

All errors are logged to stderr with clear messages and suggested solutions.</content>
<parameter name="filePath">NOTIFICATION_MANAGER_README.md