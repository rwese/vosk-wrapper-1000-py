# IPC Usage Guide

This guide explains how to use the IPC (Inter-Process Communication) features in vosk-wrapper-1000 to control the daemon and receive real-time transcription results.

## Overview

The IPC system allows you to:
- ✅ Control daemon listening state (start/stop/toggle)
- ✅ Query daemon status in real-time
- ✅ Stream live transcription results
- ✅ Retrieve session transcripts
- ✅ List available audio devices
- ✅ Build custom integrations (future vosk-webrtc-2000)

## Quick Start

### 1. Start the Daemon

```bash
# Start daemon with IPC enabled (enabled by default)
vosk-wrapper-1000 daemon --name my-mic

# Output shows:
# IPC server listening on /tmp/vosk-wrapper-my-mic.sock
# Service ready
```

### 2. Control via IPC

```bash
# Toggle listening (smart command!)
vosk-wrapper-1000 send toggle
# Output: ✓ Listening started on instance 'my-mic'

# Check status
vosk-wrapper-1000 send status
# Output:
# Instance: my-mic
# PID: 12345
# Listening: Yes
# Uptime: 45.2s
# Device: MacBook Pro Microphone
# Model: /path/to/model

# Stop listening
vosk-wrapper-1000 send stop
# Output: ✓ Stopped listening on instance 'my-mic'
```

### 3. Stream Live Transcription

```bash
# Stream with partial results
vosk-wrapper-1000 stream

# Output:
# Streaming from instance 'default' (Ctrl+C to stop)...
#
# [READY] Service ready - PID: 12345, Device: MacBook Pro Microphone
# [STATUS] Listening started
# [PARTIAL] hello wo...
# [FINAL] hello world
# [PARTIAL] how are...
# [FINAL] how are you

# Stream without partials (cleaner output)
vosk-wrapper-1000 stream --no-partials

# Output:
# [FINAL] hello world
# [FINAL] how are you
```

## Available Commands

### `send` - Send Commands to Daemon

```bash
vosk-wrapper-1000 send <command> [--name INSTANCE]
```

#### Commands

##### `toggle` - Smart Start/Stop
Automatically starts listening if stopped, stops if listening.

```bash
vosk-wrapper-1000 send toggle
# ✓ Listening started on instance 'default'

vosk-wrapper-1000 send toggle
# ✓ Listening stopped on instance 'default'
```

**Best for:** Quick control, keyboard shortcuts, scripts

##### `start` - Start Listening
```bash
vosk-wrapper-1000 send start
# ✓ Started listening on instance 'default'
```

##### `stop` - Stop Listening
```bash
vosk-wrapper-1000 send stop
# ✓ Stopped listening on instance 'default'
```

##### `status` - Get Daemon Status
```bash
vosk-wrapper-1000 send status

# Output:
# Instance: default
# PID: 12345
# Listening: Yes
# Uptime: 123.5s
# Device: MacBook Pro Microphone
# Model: /path/to/vosk-model
```

##### `transcript` - Get Session Transcript
```bash
vosk-wrapper-1000 send transcript

# Output (accumulated text since listening started):
# hello world
# how are you
# testing one two three
```

##### `devices` - List Audio Devices
```bash
vosk-wrapper-1000 send devices

# Output:
# ID    Name                                     Channels   Current
# ----------------------------------------------------------------------
# 0     MacBook Pro Microphone                   1          ✓
# 1     USB Microphone                           2
```

### `stream` - Stream Live Transcription

```bash
vosk-wrapper-1000 stream [--name INSTANCE] [--no-partials]
```

**Options:**
- `--name, -n INSTANCE`: Specify instance name (default: `default`)
- `--no-partials`: Hide partial results, only show final transcriptions

**Example:**
```bash
# Stream from specific instance
vosk-wrapper-1000 stream --name my-mic

# Stream without partial results
vosk-wrapper-1000 stream --no-partials --name my-mic
```

## Configuration

IPC settings are configured in your config file (`~/.config/vosk-wrapper-1000/config.yaml`):

```yaml
ipc:
  # Enable/disable IPC server
  enabled: true

  # Socket path template ({instance_name} is replaced)
  socket_path: "/tmp/vosk-wrapper-{instance_name}.sock"

  # Broadcast partial transcription results
  send_partials: true

  # Client request timeout (seconds)
  timeout: 5.0
```

### Environment Variables

You can override IPC settings via environment variables:

```bash
# Disable IPC
export VOSK_IPC_ENABLED=false

# Custom socket path
export VOSK_IPC_SOCKET_PATH="/var/run/vosk-{instance_name}.sock"
```

## Use Cases

### 1. Keyboard Shortcuts

Create a keyboard shortcut to toggle listening:

**macOS (Automator/Alfred):**
```bash
#!/bin/bash
vosk-wrapper-1000 send toggle
```

**Linux (i3/sway config):**
```
bindsym $mod+m exec vosk-wrapper-1000 send toggle
```

### 2. Status Bar Integration

**tmux status bar:**
```bash
#!/bin/bash
if vosk-wrapper-1000 send status 2>/dev/null | grep -q "Listening: Yes"; then
  echo "🎤"
else
  echo "🔇"
fi
```

**Waybar custom module:**
```json
{
  "custom/vosk": {
    "exec": "vosk-wrapper-1000 send status | grep Listening | cut -d: -f2",
    "interval": 2,
    "format": "🎤 {}"
  }
}
```

### 3. Integration Scripts

**Save transcript to file on stop:**
```bash
#!/bin/bash
# save_transcript.sh

vosk-wrapper-1000 send stop
vosk-wrapper-1000 send transcript > transcript_$(date +%Y%m%d_%H%M%S).txt
echo "Transcript saved!"
```

### 4. Custom Processing

**Live transcription to external service:**
```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/Users/wese/Repos/vosk-wrapper-1000/src")

from vosk_wrapper_1000.ipc_client import IPCClient

def process_transcription(event):
    if event.get("type") == "transcription" and event.get("result_type") == "final":
        text = event["text"]
        # Send to your service
        send_to_api(text)
    return True  # Continue streaming

with IPCClient("/tmp/vosk-wrapper-default.sock") as client:
    client.subscribe(["transcription"])
    for event in client.stream_events(callback=process_transcription):
        pass
```

### 5. Multi-Instance Management

```bash
# Start multiple instances
vosk-wrapper-1000 daemon --name mic1 &
vosk-wrapper-1000 daemon --name mic2 &

# Control individually
vosk-wrapper-1000 send toggle --name mic1
vosk-wrapper-1000 send toggle --name mic2

# Stream from specific instance
vosk-wrapper-1000 stream --name mic1
```

## Future: WebRTC Integration

The IPC system is designed to support future WebRTC integration via `vosk-webrtc-2000`:

```
Browser/Client ←WebRTC→ vosk-webrtc-2000 ←IPC→ vosk-wrapper-1000
```

This architecture allows:
- Remote transcription services
- Browser-based voice interfaces
- Multi-client streaming
- Language-agnostic integration

## Troubleshooting

### Connection Errors

**Error:** `Cannot connect to instance 'default'`

**Solutions:**
1. Check if daemon is running:
   ```bash
   vosk-wrapper-1000 list
   ```

2. Check socket exists:
   ```bash
   ls -la /tmp/vosk-wrapper-*.sock
   ```

3. Check IPC is enabled:
   ```bash
   grep "ipc:" ~/.config/vosk-wrapper-1000/config.yaml
   ```

### Socket Permission Issues

If you see permission errors, check socket directory:
```bash
ls -ld /tmp
chmod 1777 /tmp  # Ensure correct permissions
```

### Stale Sockets

If daemon crashed, clean up stale sockets:
```bash
rm /tmp/vosk-wrapper-*.sock
```

## Advanced: Direct Socket Communication

You can communicate directly with the socket using any programming language:

**Python Example:**
```python
import socket
import json

def send_command(instance_name, command):
    sock_path = f"/tmp/vosk-wrapper-{instance_name}.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(sock_path)

        # Send command
        request = {
            "id": "1",
            "type": "command",
            "command": command,
            "params": {}
        }
        s.sendall(json.dumps(request).encode() + b"\n")

        # Receive response
        data = s.recv(4096).decode()
        response = json.loads(data)
        return response["data"]

status = send_command("default", "status")
print(f"Listening: {status['listening']}")
```

**Node.js Example:**
```javascript
const net = require('net');

function sendCommand(instanceName, command) {
    return new Promise((resolve, reject) => {
        const sock = net.connect(`/tmp/vosk-wrapper-${instanceName}.sock`);

        sock.on('connect', () => {
            const request = {
                id: '1',
                type: 'command',
                command: command,
                params: {}
            };
            sock.write(JSON.stringify(request) + '\n');
        });

        sock.on('data', (data) => {
            const response = JSON.parse(data.toString());
            resolve(response.data);
            sock.end();
        });

        sock.on('error', reject);
    });
}

sendCommand('default', 'status').then(status => {
    console.log(`Listening: ${status.listening}`);
});
```

For detailed protocol specification, see [IPC_PROTOCOL.md](IPC_PROTOCOL.md).

## See Also

- [IPC Protocol Specification](IPC_PROTOCOL.md) - Complete protocol documentation
- [README.md](../README.md) - Main documentation
- [Configuration Guide](CONFIGURATION.md) - Configuration options
