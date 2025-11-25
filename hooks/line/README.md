# Trigger Words Hook - Python Implementation

A robust, extensible trigger word detection system for vosk-wrapper line hooks.

## Features

- **Configurable**: Easy enable/disable toggle for all triggers
- **Extensible**: Support for multiple action types:
  - Exit codes (stop listening, terminate, abort)
  - External script execution
  - Webhook calls (Slack, Discord, generic HTTP)
  - Custom Python functions
- **Regex-based**: Flexible pattern matching with case sensitivity options
- **Logging**: Comprehensive logging to stderr for debugging
- **Context-aware**: Access to both current line and full transcript

## Quick Start

### Basic Usage

```bash
# Enable triggers (default)
echo "say breaker to stop" | ./01_trigger_words.py "breaker detected"
# Exit code: 100 (Stop Listening)

# Disable all triggers
# Edit the script and set: enable_triggers = False
```

### Toggle Triggers

In `01_trigger_words.py`, line 253:

```python
# Set to True to enable, False to disable all trigger detection
enable_triggers = True  # Toggle this to enable/disable triggers
```

## Default Triggers

| Pattern | Exit Code | Action | Description |
|---------|-----------|--------|-------------|
| `\bbreaker\b` | 100 | Stop Listening | Stops the listening process |
| `\bshutdown\b` | 101 | Terminate | Terminates the application |
| `\babort\b` | 102 | Abort | Aborts current operation |

## Configuration Examples

### 1. Add Trigger with Script Execution

Call an external script when a trigger word is detected:

```python
detector.add_trigger(
    pattern=r'\bhelp\b',
    action=TriggerAction(
        name="help",
        exit_code=ExitCode.CONTINUE,
        script_path="/path/to/help_script.sh"
    ),
    description="Call help script"
)
```

The script receives:
- Argument 1: Current line text
- Stdin: Full transcript context

### 2. Add Trigger with Webhook

Send HTTP POST to a webhook when triggered:

```python
detector.add_trigger(
    pattern=r'\balert\b',
    action=TriggerAction(
        name="alert",
        exit_code=ExitCode.CONTINUE,
        webhook_url="https://hooks.example.com/alert"
    ),
    description="Send webhook alert"
)
```

Webhook payload:
```json
{
    "trigger": "alert",
    "text": "current line text",
    "context": "full transcript context"
}
```

### 3. Add Trigger with Custom Function

Execute a Python function when triggered:

```python
def my_custom_action(text: str, context: Optional[str] = None):
    # Your custom logic here
    print(f"Processing: {text}")
    # - Send emails
    # - Update databases
    # - Trigger other processes

detector.add_trigger(
    pattern=r'\bnotify\b',
    action=TriggerAction(
        name="notify",
        exit_code=ExitCode.CONTINUE,
        custom_function=my_custom_action
    ),
    description="Execute custom notification"
)
```

### 4. Complex Multi-Action Trigger

Combine multiple actions for a single trigger:

```python
detector.add_trigger(
    pattern=r'\bemergency\b',
    action=TriggerAction(
        name="emergency",
        exit_code=ExitCode.STOP_LISTENING,
        script_path="/path/to/emergency_handler.sh",
        webhook_url="https://hooks.example.com/emergency",
        custom_function=example_alert_action
    ),
    description="Emergency stop with multiple actions"
)
```

## Webhook Integration Examples

### Slack

```python
import json
import urllib.request

def send_slack_alert(text: str, context: Optional[str] = None):
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    payload = {
        "text": f"Trigger detected: {text}",
        "channel": "#alerts"
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(webhook_url, data=data)
    urllib.request.urlopen(req, timeout=5)

detector.add_trigger(
    pattern=r'\bslack\b',
    action=TriggerAction(
        name="slack",
        exit_code=ExitCode.CONTINUE,
        custom_function=send_slack_alert
    )
)
```

### Discord

```python
def send_discord_alert(text: str, context: Optional[str] = None):
    webhook_url = "https://discord.com/api/webhooks/YOUR/WEBHOOK/URL"
    payload = {
        "content": f"🚨 Alert: {text}",
        "embeds": [{
            "title": "Trigger Detected",
            "description": text,
            "color": 15158332
        }]
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(webhook_url, data=data)
    urllib.request.urlopen(req, timeout=5)

detector.add_trigger(
    pattern=r'\bdiscord\b',
    action=TriggerAction(
        name="discord",
        exit_code=ExitCode.CONTINUE,
        custom_function=send_discord_alert
    )
)
```

## External Script Examples

See `examples/help_handler.sh` for a complete example of an external script.

### Basic Script Template

```bash
#!/bin/bash
# my_trigger_script.sh

CURRENT_LINE="$1"

# Read full context from stdin
CONTEXT=$(cat)

echo "Trigger detected: $CURRENT_LINE" >&2

# Your custom logic here
# - Log to files
# - Call other services
# - Update state
# - Send notifications

exit 0
```

Make it executable:
```bash
chmod +x my_trigger_script.sh
```

## Exit Codes

| Code | Name | Purpose |
|------|------|---------|
| 0 | CONTINUE | Continue processing normally |
| 100 | STOP_LISTENING | Stop the listening process |
| 101 | TERMINATE | Terminate the application |
| 102 | ABORT | Abort current operation |

## Advanced Configuration

### JSON Configuration File

See `trigger_words_config.example.json` for a JSON-based configuration approach.

### Case Sensitivity

```python
# Case-sensitive match
detector.add_trigger(
    pattern=r'\bSTOP\b',
    action=action,
    case_sensitive=True
)

# Case-insensitive match (default)
detector.add_trigger(
    pattern=r'\bstop\b',
    action=action,
    case_sensitive=False
)
```

### Complex Patterns

```python
# Match multiple words
detector.add_trigger(
    pattern=r'\b(help|assist|support)\b',
    action=help_action
)

# Match phrases
detector.add_trigger(
    pattern=r'emergency (stop|shutdown|halt)',
    action=emergency_action
)

# Match with context
detector.add_trigger(
    pattern=r'system status',
    action=status_action
)
```

## Logging

Logs are written to stderr with timestamps:

```
2025-11-23 10:30:45 - __main__ - INFO - Trigger word 'breaker' detected in: breaker
2025-11-23 10:30:45 - __main__ - INFO - Executing action: breaker (exit code 100)
```

**Important:** Do NOT call `logging.basicConfig()` in your hooks! The main application configures logging, and `basicConfig()` only works the first time it's called. Hooks that call `basicConfig()` will prevent the application's log level settings from working.

Instead, just get a logger and use it:
```python
import logging
logger = logging.getLogger(__name__)

# Then use the logger normally:
logger.debug("Debug message")
logger.info("Info message")
```

The log level is controlled by the main application's configuration file (`config/default.yaml`).

## Testing

```bash
# Test with text
echo "test context" | ./01_trigger_words.py "breaker now"

# Test exit code
echo "test" | ./01_trigger_words.py "breaker"
echo $?  # Should output: 100

# Test with no trigger
echo "test" | ./01_trigger_words.py "normal text"
echo $?  # Should output: 0
```

## Migration from Bash Version

The Python version is a drop-in replacement for `01_trigger_words.sh`:

1. Both accept same arguments (current line as $1)
2. Both read context from stdin
3. Both use same exit codes
4. Python version adds logging to stderr

## Examples Directory

- `examples/help_handler.sh` - Example external script
- `examples/webhook_example.py` - Webhook integration examples

## Best Practices

1. **Test in safe environment first** - Verify triggers work as expected
2. **Use appropriate exit codes** - Don't abuse TERMINATE/ABORT
3. **Handle timeouts** - External scripts/webhooks should timeout quickly
4. **Log appropriately** - Use stderr for logs, not stdout
5. **Error handling** - Gracefully handle failures in custom actions
6. **Security** - Validate webhook URLs, sanitize inputs to scripts

## Troubleshooting

### Script not executing
```bash
chmod +x 01_trigger_words.py
```

### No logs appearing
Check stderr output or redirect:
```bash
./01_trigger_words.py "test" 2>&1 | less
```

### Triggers not detecting
- Check pattern regex syntax
- Verify `enable_triggers = True`
- Check case sensitivity settings

## License

Same as vosk-wrapper project.
