# vosk-wrapper-1000 Architecture

## Overview

vosk-wrapper-1000 is a cross-platform speech recognition service that uses Vosk for speech-to-text conversion. It's designed to run as a daemon with signal-based control for starting/stopping listening.

## Architecture Components

### 1. Main Service (`main.py`)
- **Daemon mode**: Runs in background, managed via PID files
- **Signal handling**: SIGUSR1 (start), SIGUSR2 (stop), SIGTERM/SIGKILL (terminate)
- **Hook system**: Extensible event hooks for start/line/stop events
- **Multi-instance support**: Named instances with PID-based management

### 2. Audio Backend Abstraction (`audio_backend.py`)
Cross-platform audio capture with pluggable backends:

#### SoundDeviceBackend (Default - Cross-platform)
- Uses `sounddevice` library (PortAudio wrapper)
- Works on: macOS, Windows, Linux (ALSA/PulseAudio/PipeWire)
- **Threading fix**: Stream creation in background thread to prevent signal blocking

#### PipeWireBackend (Linux - Future)
- Native PipeWire support via `pipewire-python`
- Better integration with modern Linux audio stack
- Currently placeholder for future implementation

### 3. Signal Handling Flow

```
User Command → send_signal_to_instance() → Process receives signal
                                                ↓
                                         signal_handler() sets flags
                                                ↓
                                         Main loop checks flags
                                                ↓
                                   Stream management (start/stop)
```

**Critical Fix**: Audio stream creation runs in a background thread (5s timeout) to ensure the main thread remains responsive to signals. Without this, the process would block indefinitely in C library calls.

### 4. Audio Processing Pipeline

For a comprehensive explanation of the complete audio processing pipeline, see **[docs/AUDIO_PROCESSING.md](docs/AUDIO_PROCESSING.md)**.

**Quick Overview:**

```
Hardware → Audio Backend → Mono Conversion → Audio Processing → VAD → Queue → Vosk Recognizer → Output
                                                    ↓
                              ┌──────────────────────────────────────┐
                              │  1. [Optional] Normalization         │
                              │  2. [Optional] Noise Reduction       │
                              │  3. [Optional] Resampling (soxr HQ)  │
                              └──────────────────────────────────────┘
```

**Key Features:**
- **Voice Activity Detection (VAD)**: Pre-roll buffering prevents cutting off word beginnings
- **Noise Filtering**: Stationary or non-stationary noise reduction with safety validation
- **Resampling**: soxr HQ streaming resampler (device rate → model rate)
- **Normalization**: Optional audio level normalization for consistent recognition
- **Non-blocking Queue**: `put_nowait()` drops frames if processing is slow
- **Hysteresis**: Allows natural pauses in speech without ending detection

**Configuration:**
```bash
# Full audio processing with all features
vosk-wrapper-1000 daemon \
  --normalize-audio \
  --noise-reduction 0.05 \
  --non-stationary-noise \
  --silence-threshold 50.0 \
  --vad-hysteresis 10 \
  --pre-roll-duration 2.0
```

### 5. Hook System (`hook_manager.py`)

Extensible event system for custom processing:

- **start**: Executed when listening begins
- **line**: Executed for each recognized line (receives full transcript + current line)
- **stop**: Executed when listening stops (receives full transcript)

Hooks can return control codes:
- `100`: Stop listening
- `101`: Terminate daemon
- `102`: Abort with  termination

## Signal Handling

### Commands
- `vosk-wrapper-1000 start [name]` - Send SIGUSR1
- `vosk-wrapper-1000 stop [name]` - Send SIGUSR2
- `vosk-wrapper-1000 terminate [name] [--force]` - Send SIGTERM or SIGKILL

### Process States
1. **Idle**: Daemon running, not listening
2. **Listening**: Audio stream active, processing speech
3. **Terminating**: Graceful shutdown in progress

## Cross-Platform Support

### Platform Detection
```python
from audio_backend import get_audio_backend
backend = get_audio_backend()  # Automatically selects best backend
```

### Current Support Matrix
| Platform | Backend | Status |
|----------|---------|--------|
| macOS | SoundDevice | ✅ Supported |
| Windows | SoundDevice | ✅ Supported |
| Linux (ALSA) | SoundDevice | ✅ Supported |
| Linux (PulseAudio) | SoundDevice | ✅ Supported |
| Linux (PipeWire) | SoundDevice | ✅ Supported (via ALSA compat) |
| Linux (PipeWire) | PipeWire (native) | 🚧 Planned |

## Threading Model

### Main Thread
- Signal handling
- Event loop (while running)
- Hook execution
- Audio queue consumption

### Audio Callback Thread
- Runs in sounddevice's internal thread
- Noise filtering
- Resampling
- Queue insertion (non-blocking)

### Stream Creation Thread
- Background thread for audio stream initialization
- 5-second timeout to prevent blocking
- Allows signals to be processed during slow initialization

## Configuration

### XDG Base Directory Support
- Models: `$XDG_DATA_HOME/vosk-wrapper-1000/models/`
- PIDs: `$XDG_CACHE_HOME/vosk-wrapper-1000/pids/`
- Hooks: `$XDG_CONFIG_HOME/vosk-wrapper-1000/hooks/`

### Optional Dependencies
```bash
# Install with PipeWire support (future)
pip install vosk-wrapper-1000[pipewire]
```

## Performance Considerations

### Audio Overflow Prevention
1. **Non-blocking queue operations**: Drops frames instead of blocking
2. **Efficient resampling**: scipy.signal.resample (faster than real-time)
3. **Optional noise filtering**: Can be disabled with `--disable-noise-filter`

### Resource Usage
- **Model loading**: ~10-15 seconds for large models (one-time cost)
- **Memory**: ~7GB for gigaspeech model (mostly model data)
- **CPU**: ~20-30% during active listening (with noise filter + resample)

## Debugging

### Enable verbose output
Run in foreground mode:
```bash
vosk-wrapper-1000 daemon --foreground --device "DeviceName"
```

### Check process state
```bash
# List all instances
vosk-wrapper-1000 list

# Check PID files
ls ~/.cache/vosk-wrapper-1000/pids/

# Monitor process signals
cat /proc/[PID]/status | grep Sig
```

## Future Enhancements

1. **PipeWire native backend**: Direct PipeWire integration for lower latency
2. **Audio preprocessing options**: VAD, gain control, etc.
3. **Streaming output**: WebSocket/HTTP streaming for real-time clients
4. **Model hot-swapping**: Change models without restart
