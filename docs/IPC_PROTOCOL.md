# Vosk Wrapper IPC Protocol Specification

Version: 1.0
Transport: Unix Domain Sockets
Format: Line-delimited JSON (one message per line, terminated by `\n`)

## Socket Location

Default: `/tmp/vosk-wrapper-{instance_name}.sock`

Example: `/tmp/vosk-wrapper-default.sock`

## Message Types

### 1. Commands (Client → Server)

Request format:
```json
{
  "id": "unique-request-id",
  "type": "command",
  "command": "command_name",
  "params": {}
}
```

#### Available Commands

##### `start`
Start listening for audio input.

Request:
```json
{"id": "1", "type": "command", "command": "start", "params": {}}
```

Response:
```json
{"id": "1", "type": "response", "success": true, "data": {"listening": true}}
```

##### `stop`
Stop listening for audio input.

Request:
```json
{"id": "2", "type": "command", "command": "stop", "params": {}}
```

Response:
```json
{"id": "2", "type": "response", "success": true, "data": {"listening": false}}
```

##### `toggle`
Toggle listening state (start if stopped, stop if started).

Request:
```json
{"id": "3", "type": "command", "command": "toggle", "params": {}}
```

Response:
```json
{"id": "3", "type": "response", "success": true, "data": {"listening": true, "action": "started"}}
```

##### `status`
Get current daemon status.

Request:
```json
{"id": "4", "type": "command", "command": "status", "params": {}}
```

Response:
```json
{
  "id": "4",
  "type": "response",
  "success": true,
  "data": {
    "listening": true,
    "pid": 12345,
    "uptime": 123.45,
    "device": "MacBook Pro Microphone",
    "device_id": 0,
    "model": "vosk-model-en-us-0.42-gigaspeech",
    "session_id": "abc-123-def-456"
  }
}
```

##### `get_transcript`
Retrieve accumulated transcript from current session.

Request:
```json
{"id": "5", "type": "command", "command": "get_transcript", "params": {}}
```

Response:
```json
{
  "id": "5",
  "type": "response",
  "success": true,
  "data": {
    "transcript": ["line 1", "line 2", "line 3"],
    "session_id": "abc-123-def-456",
    "start_time": 1234567890.123
  }
}
```

##### `get_devices`
List available audio input devices.

Request:
```json
{"id": "6", "type": "command", "command": "get_devices", "params": {}}
```

Response:
```json
{
  "id": "6",
  "type": "response",
  "success": true,
  "data": {
    "devices": [
      {"id": 0, "name": "MacBook Pro Microphone", "channels": 1},
      {"id": 1, "name": "USB Microphone", "channels": 2}
    ],
    "current_device": 0
  }
}
```

##### `subscribe`
Subscribe to event stream (transcription, status changes).

Request:
```json
{"id": "7", "type": "command", "command": "subscribe", "params": {"events": ["transcription", "status"]}}
```

Response:
```json
{"id": "7", "type": "response", "success": true, "data": {"subscribed": true}}
```

After subscribing, client will receive events (see Event Messages below).

##### `unsubscribe`
Unsubscribe from event stream.

Request:
```json
{"id": "8", "type": "command", "command": "unsubscribe", "params": {}}
```

Response:
```json
{"id": "8", "type": "response", "success": true, "data": {"subscribed": false}}
```

### 2. Responses (Server → Client)

Success response:
```json
{
  "id": "request-id",
  "type": "response",
  "success": true,
  "data": {}
}
```

Error response:
```json
{
  "id": "request-id",
  "type": "response",
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

#### Error Codes

- `INVALID_COMMAND`: Unknown command name
- `INVALID_PARAMS`: Missing or invalid parameters
- `NOT_LISTENING`: Command requires listening state but not currently listening
- `ALREADY_LISTENING`: Attempted to start when already listening
- `INTERNAL_ERROR`: Unexpected error in daemon

### 3. Events (Server → Subscribed Clients)

Events are broadcast to all subscribed clients without a request `id`.

#### `ready`
Sent when daemon completes initialization.

```json
{
  "type": "ready",
  "pid": 12345,
  "device": "MacBook Pro Microphone",
  "device_id": 0,
  "model": "vosk-model-en-us-0.42-gigaspeech",
  "timestamp": 1234567890.123
}
```

#### `transcription`
Sent when speech is recognized.

Partial result (live transcription):
```json
{
  "type": "transcription",
  "result_type": "partial",
  "text": "hello wo",
  "timestamp": 1234567890.123,
  "session_id": "abc-123-def-456"
}
```

Final result (completed phrase):
```json
{
  "type": "transcription",
  "result_type": "final",
  "text": "hello world",
  "confidence": 0.95,
  "timestamp": 1234567890.456,
  "session_id": "abc-123-def-456"
}
```

#### `status_change`
Sent when daemon state changes.

```json
{
  "type": "status_change",
  "event": "listening_started",
  "timestamp": 1234567890.123
}
```

Possible `event` values:
- `listening_started`: Audio capture started
- `listening_stopped`: Audio capture stopped
- `device_changed`: Audio device was changed
- `error`: Error occurred (includes `error` field)

#### `error`
Sent when an error occurs during operation.

```json
{
  "type": "error",
  "severity": "warning",
  "code": "AUDIO_OVERRUN",
  "message": "Audio buffer overrun detected",
  "timestamp": 1234567890.123
}
```

Severity levels: `info`, `warning`, `error`, `critical`

## Connection Lifecycle

1. **Client connects** to Unix socket
2. **Client sends commands** as needed
3. **Server sends responses** for each command
4. **(Optional) Client subscribes** to events
5. **Server broadcasts events** to subscribed clients
6. **Client disconnects** (server cleans up subscription)

## Example Session

```
Client → Server:
{"id":"1","type":"command","command":"status","params":{}}

Server → Client:
{"id":"1","type":"response","success":true,"data":{"listening":false,"pid":12345}}

Client → Server:
{"id":"2","type":"command","command":"subscribe","params":{"events":["transcription","status"]}}

Server → Client:
{"id":"2","type":"response","success":true,"data":{"subscribed":true}}

Client → Server:
{"id":"3","type":"command","command":"start","params":{}}

Server → Client:
{"id":"3","type":"response","success":true,"data":{"listening":true}}

Server → Client (broadcast):
{"type":"status_change","event":"listening_started","timestamp":1234567890.123}

Server → Client (broadcast):
{"type":"transcription","result_type":"partial","text":"hello","timestamp":1234567890.234}

Server → Client (broadcast):
{"type":"transcription","result_type":"final","text":"hello world","confidence":0.95,"timestamp":1234567890.456}
```

## Protocol Notes

- **Line-delimited**: Each message is a single line terminated by `\n`
- **JSON encoding**: All messages are valid JSON objects
- **Request IDs**: Client-generated, echo'd in response for matching
- **Timestamps**: Unix timestamp with millisecond precision (float)
- **Session IDs**: UUID format, resets when daemon restarts
- **Backward compatibility**: Future versions may add fields but won't remove existing ones

## Client Implementation Guidelines

- Use non-blocking I/O or select/poll for reading
- Handle partial line reads (buffer until `\n` received)
- Implement timeout for responses (recommend 5 seconds)
- Reconnect automatically if socket closes
- Generate unique request IDs (UUID recommended)
- Parse events even if not subscribed (for `ready` event)

## Server Implementation Guidelines

- Accept multiple concurrent client connections
- Maintain per-client subscription state
- Broadcast events only to subscribed clients
- Clean up client state on disconnect
- Log protocol errors but don't crash daemon
- Use non-blocking I/O to avoid blocking audio processing
