# WebRTC Speech Recognition Examples

This directory contains examples for using vosk-wrapper-1000's WebRTC functionality to perform browser-based speech recognition.

## Files

- **`webrtc_client.html`** - Browser-based WebRTC client for real-time speech recognition
- **`webrtc_demo.py`** - All-in-one demo script that starts both the daemon and HTTP server
- **`serve_client.py`** - Standalone HTTP server for the WebRTC client (daemon must be running separately)

## Quick Start

### Option 1: All-in-One Demo (Recommended for first-time users)

This starts both the vosk-wrapper daemon and the HTTP server:

```bash
cd examples/webrtc
python webrtc_demo.py --model vosk-model-en-us-0.22
```

Then open your browser to: `http://localhost:8001/webrtc_client.html`

### Option 2: Separate Daemon and Client Server

**Step 1: Start the daemon with WebRTC enabled**

```bash
python -m vosk_wrapper_1000.main daemon \
    --webrtc-enabled \
    --webrtc-port 8080 \
    --model vosk-model-en-us-0.22 \
    --name webrtc-demo
```

**Step 2: Start the client server**

```bash
cd examples/webrtc
python serve_client.py --port 8001
```

Then open your browser to: `http://localhost:8001/webrtc_client.html`

## Using the WebRTC Client

1. **Open the client** in your browser (Chrome, Firefox, or Safari recommended)
2. **Click "Connect to Server"** - This establishes the WebRTC connection
3. **Grant microphone permissions** when prompted by your browser
4. **Click "Start Recognition"** to begin transcribing your speech
5. **Speak into your microphone** - Transcriptions will appear in real-time
6. **Click "Stop Recognition"** when finished

## Configuration

### Daemon Options

- `--webrtc-port PORT` - Port for WebRTC signaling server (default: 8080)
- `--webrtc-host HOST` - Host to bind WebRTC server (default: 0.0.0.0)
- `--model PATH` - Path to Vosk model or model name

### Client Server Options

- `--port PORT` - HTTP server port (default: 8001)
- `--host HOST` - Host to bind HTTP server (default: localhost)
- `--https` - Use HTTPS (generates self-signed certificate if needed)

## Port Configuration

By default:
- **WebRTC signaling server**: Port 8080 (HTTP/JSON API)
- **Client HTTP server**: Port 8001 (serves HTML/JS)

If port 8080 is already in use, you can change it:

```bash
# Start daemon on port 8081
python -m vosk_wrapper_1000.main daemon --webrtc-enabled --webrtc-port 8081 ...

# Update the client HTML to connect to port 8081
# Edit webrtc_client.html, change the default server URL input value
```

## HTTPS/SSL Support

For microphone access on non-localhost domains, HTTPS is required:

```bash
# serve_client.py will auto-generate self-signed certificates
python serve_client.py --https --port 8001
```

Your browser will show a security warning for self-signed certificates - this is expected for local development.

## Architecture

```
┌─────────────────┐          ┌──────────────────────┐
│   Browser       │          │  vosk-wrapper-1000   │
│                 │          │      Daemon          │
│  ┌───────────┐  │          │                      │
│  │ HTML/JS   │  │  HTTP    │  ┌────────────────┐  │
│  │  Client   │◄─┼──────────┼─►│ HTTP Server    │  │
│  └─────┬─────┘  │ (8001)   │  │ (WebRTC API)   │  │
│        │        │          │  └────────┬───────┘  │
│        │        │          │           │          │
│  ┌─────▼─────┐  │          │  ┌────────▼───────┐  │
│  │ WebRTC    │  │  WebRTC  │  │ WebRTC Server  │  │
│  │Peer Conn. │◄─┼──────────┼─►│ (aiortc)       │  │
│  └─────┬─────┘  │ (8080)   │  └────────┬───────┘  │
│        │        │          │           │          │
│  ┌─────▼─────┐  │          │  ┌────────▼───────┐  │
│  │Microphone │  │   Audio  │  │ Audio Processor│  │
│  └───────────┘  │  Stream  │  │ + Vosk Model   │  │
│                 │          │  └────────────────┘  │
└─────────────────┘          └──────────────────────┘
```

## Features

- **Real-time speech recognition** from browser microphone
- **Voice Activity Detection (VAD)** - Only processes speech, ignores silence
- **Noise reduction** - Same high-quality audio processing as local microphone
- **Multiple simultaneous connections** - Support for multiple browser clients
- **Browser compatibility** - Works with Chrome, Firefox, Safari, and Edge

## Troubleshooting

### "Connection failed" or "Server error: 500"

- Ensure the daemon is running with `--webrtc-enabled`
- Check that port 8080 is not blocked by a firewall
- Verify the server URL in the client matches your daemon's port

### "Microphone access requires HTTPS"

- For non-localhost access, use HTTPS: `python serve_client.py --https`
- Or access via `localhost` or `127.0.0.1` which don't require HTTPS

### No transcription appearing

- Check browser console for errors (F12)
- Verify microphone permissions were granted
- Ensure you clicked "Start Recognition" after connecting
- Check daemon logs for audio processing errors

### Port already in use

- Kill existing processes: `pkill -f vosk_wrapper_1000`
- Or use different ports: `--webrtc-port 8081` and `--port 8002`

## Requirements

The WebRTC functionality requires these additional Python packages:

- `aiortc>=1.6.0` - WebRTC implementation
- `aiohttp>=3.8.0` - HTTP server for signaling
- `av>=10.0.0` - Media processing

These are included in the main package dependencies.

## Browser Requirements

- **Chrome/Chromium** 74+ (recommended)
- **Firefox** 66+
- **Safari** 12.1+
- **Edge** 79+

All modern browsers with WebRTC support should work.

## See Also

- [WebRTC Documentation](../../docs/WEBRTC.md) - Detailed technical documentation
- [Main README](../../README.md) - General vosk-wrapper-1000 documentation
