# Persistent Recording Notifications

These hooks provide persistent desktop notifications that show recording status throughout the entire session, rather than notifying for each individual transcribed line.

## Available Scripts

### Basic Persistent Notifications
- **02_persistent_notification.py** (start/stop): Simple persistent notification that shows when recording starts and stops

### Advanced Persistent Notifications
- **03_advanced_persistent_notification.py** (start/stop): Enhanced version with detailed statistics, duration tracking, and performance metrics

## How It Works

1. **Start Hook**: Creates a persistent notification when recording begins
2. **During Recording**: The notification remains visible showing "Recording Active"
3. **Stop Hook**: Updates the notification with final statistics and completion status

## Installation

### Basic Version
```bash
# Copy to hook directories
cp hooks/start/02_persistent_notification.py ~/.config/vosk-wrapper-1000/hooks/start/
cp hooks/stop/02_persistent_notification.py ~/.config/vosk-wrapper-1000/hooks/stop/

# Make executable
chmod +x ~/.config/vosk-wrapper-1000/hooks/start/02_persistent_notification.py
chmod +x ~/.config/vosk-wrapper-1000/hooks/stop/02_persistent_notification.py
```

### Advanced Version
```bash
# Copy to hook directories
cp hooks/start/03_advanced_persistent_notification.py ~/.config/vosk-wrapper-1000/hooks/start/
cp hooks/stop/03_advanced_persistent_notification.py ~/.config/vosk-wrapper-1000/hooks/stop/

# Make executable
chmod +x ~/.config/vosk-wrapper-1000/hooks/start/03_advanced_persistent_notification.py
chmod +x ~/.config/vosk-wrapper-1000/hooks/stop/03_advanced_persistent_notification.py
```

## Requirements

```bash
# Install notification system
sudo apt install libnotify-bin

# Test notifications
notify-send "Test" "This should work"
```

## Features

### Basic Version
- ✅ Persistent notification during recording
- ✅ Shows start/stop status
- ✅ Automatic cleanup
- ✅ Works across desktop environments
- ✅ Transient notifications (don't clutter notification center)

### Advanced Version
- ✅ All basic features
- ✅ Recording duration tracking
- ✅ Word count statistics
- ✅ Words per minute calculation
- ✅ Session timing information
- ✅ JSON status file for extensibility
- ✅ Transient notifications (don't clutter notification center)

## Usage Examples

### Start Recording Session
```bash
vosk-wrapper-1000 daemon
vosk-wrapper-1000 start
# Persistent notification appears: "🎤 Recording Active"
```

### During Recording
- Notification remains visible in system tray
- Shows continuous recording status
- Can be clicked to bring focus to terminal

### Stop Recording Session
```bash
vosk-wrapper-1000 stop
# Notification updates: "⏹️ Recording Complete" with statistics
```

## Configuration

### Basic Version
The scripts use default settings. No configuration needed.

### Advanced Version
Edit the scripts to customize:
```python
# In both start and stop hooks
self.show_word_count = True      # Show word count in notifications
self.show_duration = True       # Show recording duration
self.update_interval = 30       # Status update interval (seconds)
```

## Notification Behavior

### Persistence
- **Start**: Creates notification that doesn't auto-dismiss
- **Stop**: Updates notification and auto-dismisses after 5 seconds

### Desktop Integration
- Uses `x-canonical-private-synchronous` hint for proper replacement
- **Transient notifications** - don't appear in notification center/panel
- Works with GNOME, KDE, XFCE, and other desktop environments
- Notifications appear in system tray only (less intrusive)

### Status Tracking
- Status saved to `~/.cache/vosk-wrapper-1000/`
- Automatic cleanup when recording stops
- JSON format for extensibility

## Troubleshooting

### Notifications Not Appearing
```bash
# Check if notify-send works
notify-send "Test" "Hello World"

# Check notification daemon
systemctl --user status dunst  # or whatever notification daemon you use
```

### Status File Issues
```bash
# Check status directory
ls -la ~/.cache/vosk-wrapper-1000/

# Manual cleanup
rm ~/.cache/vosk-wrapper-1000/*notification_status*
```

### Permission Issues
```bash
# Ensure scripts are executable
ls -la ~/.config/vosk-wrapper-1000/hooks/start/02_persistent_notification.py

# Check directory permissions
ls -ld ~/.config/vosk-wrapper-1000/
ls -ld ~/.cache/vosk-wrapper-1000/
```

## Advanced Usage

### Custom Notification Content
Edit the scripts to customize notification messages:
```python
# In start hook
title = "🎤 My Custom Recording Status"
message = f"Session started at {timestamp}"

# In stop hook
title = "✅ Session Complete"
message = f"Recorded {word_count} words in {duration}"
```

### Integration with Other Tools
The status files can be read by other scripts:
```bash
# Check if recording is active
cat ~/.cache/vosk-wrapper-1000/notification_status

# Get advanced statistics
cat ~/.cache/vosk-wrapper-1000/advanced_notification_status.json | jq
```

## Comparison with Line Notifications

| Feature | Line Notifications | Persistent Notifications |
|---------|-------------------|-------------------------|
| Frequency | Every transcribed line | Start/stop events only |
| Information | Individual phrases | Session statistics |
| Persistence | Auto-dismiss quickly | Remains visible |
| Use Case | Real-time feedback | Status monitoring |
| Performance | Higher overhead | Lower overhead |

## Best Practices

1. **Choose appropriate version** based on your needs
2. **Test in your desktop environment** first
3. **Monitor notification daemon** for issues
4. **Clean up status files** if needed
5. **Customize messages** for your workflow

## Examples in Action

### Basic Workflow
```
1. vosk-wrapper-1000 start
   → "🎤 Recording Active" notification appears

2. User speaks for 5 minutes
   → Notification stays visible

3. vosk-wrapper-1000 stop
   → "⏹️ Recording Stopped" notification appears
```

### Advanced Workflow
```
1. vosk-wrapper-1000 start
   → "🎤 Recording Active - Started at 14:30:00" appears

2. User speaks, system tracks statistics
   → Notification shows live updates

3. vosk-wrapper-1000 stop
   → "⏹️ Recording Complete - Duration: 00:05:23, Words: 147, Speed: 28.2 WPM"
```</content>
<parameter name="filePath">hooks/start/PERSISTENT_NOTIFICATIONS_README.md