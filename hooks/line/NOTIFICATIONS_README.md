# Notification Hooks - Real-time Alerts During Recording

This directory contains Python scripts that create notifications while vosk-wrapper-1000 is actively recording speech. These hooks are called for each transcribed line, providing real-time feedback.

## Available Scripts

### 05_notifications.py - Basic Desktop Notifications
- **Purpose**: Simple desktop notifications with optional sound alerts
- **Features**:
  - Desktop notifications using `notify-send`
  - Sound alerts for important keywords
  - Automatic filtering of short text
  - Visual feedback with emojis

### 06_advanced_notifications.py - Multi-Method Notifications
- **Purpose**: Comprehensive notification system with multiple methods
- **Features**:
  - Desktop notifications with urgency levels
  - Webhook support (Slack, Discord, generic)
  - Sound alerts with fallback audio players
  - Async webhook sending for performance
  - Urgent keyword detection
  - Performance monitoring

### 07_webhook_notifications.py - Webhook-Only Notifications
- **Purpose**: Focused webhook notifications for external services
- **Features**:
  - Support for Slack, Discord, and generic webhooks
  - Asynchronous sending (non-blocking)
  - Retry logic with exponential backoff
  - Configurable filtering
  - JSON payloads with full context

## Installation

1. **Copy scripts to hooks directory**:
   ```bash
   mkdir -p ~/.config/vosk-wrapper-1000/hooks/line/
   cp hooks/line/05_notifications.py ~/.config/vosk-wrapper-1000/hooks/line/
   cp hooks/line/06_advanced_notifications.py ~/.config/vosk-wrapper-1000/hooks/line/
   cp hooks/line/07_webhook_notifications.py ~/.config/vosk-wrapper-1000/hooks/line/
   ```

2. **Make executable**:
   ```bash
   chmod +x ~/.config/vosk-wrapper-1000/hooks/line/05_notifications.py
   chmod +x ~/.config/vosk-wrapper-1000/hooks/line/06_advanced_notifications.py
   chmod +x ~/.config/vosk-wrapper-1000/hooks/line/07_webhook_notifications.py
   ```

3. **Install dependencies**:
   ```bash
   # For desktop notifications
   sudo apt install libnotify-bin

   # For sound notifications (optional)
   sudo apt install sox alsa-utils pulseaudio-utils
   ```

## Configuration

### Desktop Notifications (05_notifications.py)
Edit the script to customize:
```python
self.icon = "audio-input-microphone"  # Notification icon
self.timeout = 3000  # Display duration in milliseconds
self.sound_enabled = True  # Enable/disable sound
self.sound_file = "/usr/share/sounds/freedesktop/stereo/message.oga"
```

### Advanced Notifications (06_advanced_notifications.py)
Edit the `NotificationConfig` class:
```python
# Desktop settings
self.desktop_enabled = True
self.desktop_icon = "audio-input-microphone"
self.desktop_timeout = 3000

# Webhook settings
self.webhook_enabled = False
self.webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
self.webhook_service = "slack"  # slack, discord, generic

# Sound settings
self.sound_enabled = True
self.sound_file = "/usr/share/sounds/freedesktop/stereo/message.oga"

# Filtering
self.min_length = 2
self.urgent_keywords = ["help", "emergency", "stop", "shutdown", "abort"]
self.quiet_keywords = ["um", "uh", "like", "you know"]
```

### Webhook Notifications (07_webhook_notifications.py)
Edit the `WebhookNotifier.__init__` method:
```python
self.enabled = True
self.service = "slack"  # "slack", "discord", or "generic"
self.webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
self.min_length = 3
self.skip_keywords = ["um", "uh", "like"]
```

## Usage Examples

### Basic Desktop Notifications
```bash
# Start recording
vosk-wrapper-1000 daemon
vosk-wrapper-1000 start

# Say something - you'll see desktop notifications for each phrase
# "Hello world" -> Desktop notification appears
```

### Webhook Notifications
```python
# In 07_webhook_notifications.py, set:
self.webhook_url = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
self.service = "slack"
self.enabled = True

# Start recording - notifications sent to Slack
```

### Discord Integration
```python
# In 06_advanced_notifications.py or 07_webhook_notifications.py:
self.webhook_url = "https://discord.com/api/webhooks/YOUR/WEBHOOK/ID"
self.service = "discord"
```

## Testing

Test scripts individually:
```bash
# Test desktop notifications
echo "test notification" | ./05_notifications.py "Hello world"

# Test webhook (configure URL first)
echo "full context here" | ./07_webhook_notifications.py "Test message"
```

## Troubleshooting

### No Desktop Notifications
```bash
# Check if notify-send is installed
which notify-send

# Test manually
notify-send "Test" "This should work"
```

### Webhook Errors
- Verify webhook URL is correct
- Check network connectivity
- Review service-specific payload formats
- Check webhook service logs

### Sound Not Working
```bash
# Test audio playback
paplay /usr/share/sounds/freedesktop/stereo/message.oga

# Alternative players
aplay /usr/share/sounds/freedesktop/stereo/message.oga
play /usr/share/sounds/freedesktop/stereo/message.oga
```

### Performance Issues
- Use async webhooks for better performance
- Increase webhook timeouts if needed
- Monitor stderr logs for timing information

## Hook Behavior

- **Called for each transcribed line** during active recording
- **Receives current line** as first argument
- **Receives full context** via stdin
- **Should exit quickly** to avoid blocking transcription
- **Use stderr for logging** (stdout is for transcription)
- **Return appropriate exit codes** for control flow

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Continue | Normal processing |
| 100 | Stop Listening | End recording session |
| 101 | Terminate | Stop daemon completely |
| 102 | Stop & Terminate | Stop recording and daemon |

## Examples Directory

- `examples/webhook_example.py` - Advanced webhook examples
- `examples/help_handler.sh` - Simple bash hook example

## Security Notes

- **Validate webhook URLs** before enabling
- **Use HTTPS** for webhook endpoints
- **Don't log sensitive information** to stderr
- **Consider rate limiting** for high-frequency notifications</content>
<parameter name="filePath">hooks/line/NOTIFICATIONS_README.md