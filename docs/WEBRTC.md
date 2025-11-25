# WebRTC Support for vosk-wrapper-1000

vosk-wrapper-1000 includes built-in WebRTC support, allowing browser-based clients to connect directly to the speech recognition daemon for real-time audio processing.

## Overview

WebRTC (Web Real-Time Communication) enables direct peer-to-peer communication between browsers and the vosk-wrapper-1000 daemon. This allows for:

- Browser-based speech recognition without server-side audio processing
- Real-time transcription in web applications
- Direct audio streaming from browser microphone to Vosk engine
- Low-latency speech recognition for web interfaces

## Architecture

The WebRTC implementation consists of:

1. **WebRTC Server**: Integrated into the daemon process, handles WebRTC signaling and peer connections
2. **Audio Processing**: WebRTC audio streams are processed through the same pipeline as microphone input
3. **Signaling Protocol**: HTTP-based signaling for WebRTC offer/answer exchange
4. **Client Example**: HTML/JavaScript client for testing and integration

## Configuration

WebRTC is configured in the main configuration file (`~/.config/vosk-wrapper-1000/config.yaml`):

```yaml
webrtc:
  # Enable WebRTC server
  enabled: true

  # Server port
  port: 8080

  # Server host (0.0.0.0 for all interfaces)
  host: "0.0.0.0"

  # STUN servers for NAT traversal
  stun_servers:
    - "stun:stun.l.google.com:19302"

  # TURN servers for NAT traversal (optional)
  turn_servers: []

  # Maximum concurrent connections
  max_connections: 5

  # Audio codec format
  audio_format: "opus"

  # Audio sample rate
  sample_rate: 48000

  # Number of audio channels
  channels: 1
```

### Environment Variables

WebRTC can also be configured via environment variables:

- `VOSK_WEBRTC_ENABLED=true` - Enable WebRTC server
- `VOSK_WEBRTC_PORT=8080` - Set server port
- `VOSK_WEBRTC_HOST=0.0.0.0` - Set server host

### Command Line Options

When starting the daemon:

```bash
# Enable WebRTC with default settings
vosk-wrapper-1000 daemon --webrtc-enabled

# Enable WebRTC with custom port
vosk-wrapper-1000 daemon --webrtc-enabled --webrtc-port 9000

# Enable WebRTC with custom host
vosk-wrapper-1000 daemon --webrtc-enabled --webrtc-host 127.0.0.1
```

## Starting the WebRTC Server

1. **Enable WebRTC in configuration** or use command-line flags
2. **Start the daemon** with WebRTC enabled:

```bash
vosk-wrapper-1000 daemon --webrtc-enabled
```

3. **Verify the server is running**:

```bash
# Check daemon status
vosk-wrapper-1000 send --name default --ipc-command webrtc_status

# Or check via IPC
vosk-wrapper-1000 send --name default --ipc-command status
```

## WebRTC API

The WebRTC server provides an HTTP-based signaling API:

### GET /

Returns server information:

```json
{
  "server": "vosk-wrapper-1000 WebRTC",
  "version": "1.0.0",
  "status": "running",
  "max_connections": 5,
  "active_connections": 0
}
```

### POST /offer

Request a WebRTC offer from the server. Returns:

```json
{
  "peer_id": "uuid-string",
  "type": "offer",
  "sdp": "WebRTC SDP offer"
}
```

### POST /answer/{peer_id}

Send WebRTC answer to complete connection:

```json
{
  "sdp": "WebRTC SDP answer"
}
```

Returns: `{"status": "connected"}`

### DELETE /peer/{peer_id}

Disconnect a peer connection.

### GET /status

Get detailed server status:

```json
{
  "running": true,
  "host": "0.0.0.0",
  "port": 8080,
  "active_connections": 1,
  "max_connections": 5,
  "total_peers": 2,
  "peers": {
    "peer-uuid-1": {
      "peer_id": "peer-uuid-1",
      "connected": true,
      "connected_at": 1234567890.123,
      "last_activity": 1234567890.456,
      "connection_state": "connected"
    }
  }
}
```

## IPC Commands

WebRTC can be controlled via IPC commands:

```bash
# Get WebRTC server status
vosk-wrapper-1000 send --name default --ipc-command webrtc_status

# Start WebRTC server (if configured but not started)
vosk-wrapper-1000 send --name default --ipc-command start_webrtc

# Stop WebRTC server
vosk-wrapper-1000 send --name default --ipc-command stop_webrtc
```

## Client Integration

### Using the Example Client

1. **Start the daemon** with WebRTC enabled
2. **Open the client** in a web browser: `examples/webrtc/webrtc_client.html`
3. **Configure the server URL** (default: http://localhost:8080)
4. **Click "Connect to Server"**
5. **Grant microphone permissions** when prompted
6. **Click "Start Recognition"** to begin transcription

### Browser Requirements

- **HTTPS Required**: Microphone access requires secure context
- **WebRTC Support**: Modern browsers (Chrome 28+, Firefox 22+, Safari 11+)
- **Microphone Permissions**: User must grant microphone access

### Custom Client Implementation

```javascript
class VoskWebRTCClient {
    async connect(serverUrl) {
        // Request offer from server
        const response = await fetch(`${serverUrl}/offer`, {
            method: 'POST'
        });
        const offerData = await response.json();

        // Create RTCPeerConnection
        const pc = new RTCPeerConnection({
            iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
        });

        // Get microphone access
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: { sampleRate: 48000, channelCount: 1 }
        });

        // Add audio track
        stream.getTracks().forEach(track => pc.addTrack(track, stream));

        // Set remote description
        await pc.setRemoteDescription({
            type: 'offer',
            sdp: offerData.sdp
        });

        // Create and send answer
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);

        await fetch(`${serverUrl}/answer/${offerData.peer_id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sdp: answer.sdp })
        });

        // Wait for connection
        return new Promise((resolve, reject) => {
            pc.onconnectionstatechange = () => {
                if (pc.connectionState === 'connected') {
                    resolve(pc);
                } else if (pc.connectionState === 'failed') {
                    reject(new Error('Connection failed'));
                }
            };
        });
    }
}
```

## Audio Processing

WebRTC audio streams are processed through the same pipeline as microphone input:

1. **Audio Reception**: WebRTC audio frames received from browser
2. **Format Conversion**: Convert to 16-bit PCM at model sample rate
3. **Noise Reduction**: Apply noise reduction if enabled
4. **Voice Activity Detection**: Detect speech segments
5. **Vosk Recognition**: Process through Vosk speech recognition engine
6. **Transcription Events**: Generate transcription events via IPC

## Security Considerations

- **HTTPS Required**: WebRTC requires secure context for microphone access
- **CORS Headers**: Server includes CORS headers for browser access
- **Connection Limits**: Configurable maximum concurrent connections
- **Input Validation**: All signaling requests are validated

## Troubleshooting

### Connection Issues

1. **Check server status**:
   ```bash
   vosk-wrapper-1000 send --name default --ipc-command webrtc_status
   ```

2. **Verify port availability**:
   ```bash
   netstat -tlnp | grep :8080
   ```

3. **Check firewall settings** for WebRTC port

### Audio Issues

1. **Browser permissions**: Ensure microphone access is granted
2. **HTTPS requirement**: Access client via HTTPS or localhost
3. **Audio format**: Verify browser supports requested audio constraints

### Performance Issues

1. **Connection limits**: Reduce `max_connections` if experiencing issues
2. **Audio processing**: Monitor CPU usage during WebRTC sessions
3. **Network quality**: WebRTC requires stable network connection

## Examples

### Basic WebRTC Setup

```bash
# Enable WebRTC in daemon
vosk-wrapper-1000 daemon --webrtc-enabled --name webrtc-demo

# Check status
vosk-wrapper-1000 send --name webrtc-demo --ipc-command webrtc_status

# Open client in browser
# Navigate to examples/webrtc/webrtc_client.html
```

### Integration with Web Application

```javascript
// Connect to vosk-wrapper-1000 WebRTC
const client = new VoskWebRTCClient();
await client.connect('http://localhost:8080');

// Start recognition
client.startRecognition();

// Listen for transcription events
client.onTranscription = (text, confidence) => {
    console.log('Transcription:', text, 'Confidence:', confidence);
};
```

## Limitations

- **Browser Compatibility**: Requires modern WebRTC-supporting browsers
- **HTTPS Requirement**: Microphone access requires secure context
- **Network Dependency**: WebRTC requires stable network connection
- **Single Peer**: Current implementation supports one active connection per daemon instance
- **Audio Format**: Limited to Opus codec and 48kHz sample rate

## Future Enhancements

- Multiple simultaneous peer connections
- Custom STUN/TURN server configuration
- Advanced audio processing options
- WebRTC data channels for bidirectional communication
- Browser extension support
