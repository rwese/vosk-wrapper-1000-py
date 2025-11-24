# Vosk Wrapper 1000

A simple, robust, and configurable Python-based speech recognition service using [Vosk](https://alphacephei.com/vosk/).

**Repository**: [github.com/rwese/vosk-wrapper-1000-py](https://github.com/rwese/vosk-wrapper-1000-py)

## 🚀 **What's New in v2.0**

### **Major Architecture Refactoring**
- **Modular Design**: Transformed from monolithic 470-line file to 13 focused modules for better maintainability
- **Enhanced Audio Processing**: Upgraded to soxr HQ streaming resampling with configurable noise filtering
- **Audio Recording**: Record processed audio to WAV files for review and debugging
- **Cross-Platform Audio System Detection**: Automatic detection of PipeWire/PulseAudio/ALSA/CoreAudio/WASAPI
- **Improved Device Management**: Enhanced device compatibility validation and management
- **Project Renaming**: Renamed from "vosk-simple" to "vosk-wrapper-1000" for better clarity

### **New Features**
- **Configurable Noise Reduction**: `--noise-reduction 0.0-1.0` (default: 0.2)
- **Noise Type Selection**: `--stationary-noise` vs `--non-stationary-noise`
- **Audio Recording**: `--record-audio filename.wav` records exactly what Vosk receives
- **Enhanced CLI**: Better help, examples, and error handling
- **Audio System Info**: Detailed audio backend information for troubleshooting
- **Modern Build System**: Full uv support with proper Python packaging

## Installation

Install directly from GitHub using uv or pip:

```bash
# Using uv (recommended)
uv tool install git+https://github.com/rwese/vosk-wrapper-1000-py

# Using pip
pip install git+https://github.com/rwese/vosk-wrapper-1000-py
```

After installation, the commands `vosk-wrapper-1000` and `vosk-download-model-1000` will be available in your PATH.

## Quick Start

### Using Installed Commands

If you installed the package, use the commands directly:

1.  **Download a Model**
    ```bash
    # List all available models (default when no arguments)
    vosk-download-model-1000

    # List only installed models
    vosk-download-model-1000 --installed

    # Download a specific model (e.g., small English model)
    vosk-download-model-1000 vosk-model-small-en-us-0.15

    # Delete a model
    vosk-download-model-1000 --delete vosk-model-small-en-us-0.15
    ```

2.  **Start the Daemon**
    ```bash
    # Run with default settings (runs as daemon in background)
    vosk-wrapper-1000 daemon

    # Run in foreground (useful for debugging)
    vosk-wrapper-1000 daemon --foreground

    # Run with a custom instance name for managing multiple processes
    vosk-wrapper-1000 daemon --name my-instance

    # List available audio devices and their sample rates
    vosk-wrapper-1000 daemon --list-devices

    # Run with specific settings
    vosk-wrapper-1000 daemon --name my-instance \
      --device "Microphone Name" \
      --samplerate 48000 \
      --model ~/.local/share/vosk-wrapper-1000/models/vosk-model-small-en-us-0.15

    # Run with advanced Vosk options
    vosk-wrapper-1000 daemon \
      --words \                   # Enable word-level timestamps
      --partial-words \           # Enable partial results
      --grammar "yes no stop go"  # Restrict vocabulary

    # Enhanced audio processing options
    vosk-wrapper-1000 daemon \
      --noise-reduction 0.3 \     # Stronger noise reduction (0.0-1.0)
      --non-stationary-noise \   # Adaptive noise filtering (slower)
      --record-audio output.wav   # Record processed audio

    # Run without noise filtering (if needed)
    vosk-wrapper-1000 daemon --disable-noise-filter
    ```

3.  **Control Running Instances**
    ```bash
    # List all running instances
    vosk-wrapper-1000 list

    # Start listening (sends SIGUSR1)
    vosk-wrapper-1000 start              # for "default" instance
    vosk-wrapper-1000 start my-instance  # for named instance

    # Stop listening (sends SIGUSR2)
    vosk-wrapper-1000 stop               # for "default" instance
    vosk-wrapper-1000 stop my-instance   # for named instance

    # Terminate an instance (sends SIGTERM)
    vosk-wrapper-1000 terminate              # for "default" instance
    vosk-wrapper-1000 terminate my-instance  # for named instance
    ```

### Running from Source with uvx

If you cloned the repository and want to run without installing:

1.  **Download a Model**
    ```bash
    # List all available models
    uvx --from . vosk-download-model-1000

    # Download a specific model
    uvx --from . vosk-download-model-1000 vosk-model-small-en-us-0.15
    ```

2.  **Run and Control the Application**
    ```bash
    # Run with default settings
    uvx --from . vosk-wrapper-1000 daemon

    # Run with a named instance
    uvx --from . vosk-wrapper-1000 daemon --name my-instance --device "Microphone Name"

    # Control instances
    uvx --from . vosk-wrapper-1000 list
    uvx --from . vosk-wrapper-1000 start my-instance
    uvx --from . vosk-wrapper-1000 stop my-instance
    ```

### Alternative: Development Setup

If you prefer to develop locally or don't want to use uvx:

1.  **Install Dependencies**
    ```bash
    # Using uv (recommended)
    uv pip install -e .

    # Or using pip
    pip install -e .
    ```

2.  **Download a Model**
    ```bash
    # List all available models
    uv run python -m vosk_wrapper_1000.download_model

    # Download a specific model
    uv run python -m vosk_wrapper_1000.download_model vosk-model-small-en-us-0.15

    # Delete a model
    uv run python -m vosk_wrapper_1000.download_model --delete vosk-model-small-en-us-0.15
    ```

3.  **Run the Application**
    ```bash
    # Run with default settings
    uv run python -m vosk_wrapper_1000.main daemon

    # Or with options:
    uv run python -m vosk_wrapper_1000.main daemon --list-devices
    uv run python -m vosk_wrapper_1000.main daemon --device "Microphone Name"
    ```

## Automatic Sample Rate Handling

Vosk-wrapper-1000 automatically handles sample rate mismatches between your audio device and the model:

1. **Auto-detection**: Reads the model's required sample rate from `conf/mfcc.conf`
2. **Device native rate**: Always uses your device's native sample rate for recording
3. **Automatic resampling**: Transparently resamples audio from device rate to model rate

This means you don't need to worry about sample rates - just run the application and it will work with any audio device!

Example:
```bash
# Device runs at 48000 Hz, model expects 16000 Hz
# Resampling happens automatically
vosk-wrapper-1000 daemon
# Output: Device rate: 48000 Hz, Model rate: 16000 Hz
# Output: Audio will be resampled from 48000 Hz to 16000 Hz
```

## Enhanced Audio Processing

### **High-Quality Audio Resampling**

Vosk-wrapper-1000 now uses **soxr** for high-quality streaming resampling:
- **HQ Quality**: Better than scipy resampling with optimized algorithms
- **Streaming**: Real-time resampling with proper chunking and finalization
- **Automatic**: Handles any device-to-model sample rate conversion transparently

### **Configurable Noise Filtering**

Advanced noise reduction using the **noisereduce** library with configurable options:

```bash
# Configure noise reduction strength (0.0-1.0, default: 0.2)
vosk-wrapper-1000 daemon --noise-reduction 0.3

# Choose noise type (default: stationary)
vosk-wrapper-1000 daemon --stationary-noise      # Faster, good for constant noise
vosk-wrapper-1000 daemon --non-stationary-noise  # Slower, adapts to changing noise

# Disable noise filtering completely
vosk-wrapper-1000 daemon --disable-noise-filter
```

**Noise Reduction Types:**
- **Stationary** (default): Optimized for constant background noise (fans, AC, hum)
- **Non-stationary**: Adapts to changing noise patterns (better for variable environments)

### **Audio Recording**

Record exactly what Vosk receives for review and debugging:

```bash
# Record processed audio to WAV file
vosk-wrapper-1000 daemon --record-audio session.wav

# Combine with other options
vosk-wrapper-1000 daemon \
  --record-audio debug_session.wav \
  --noise-reduction 0.4 \
  --device "USB Microphone"
```

The recording includes all processing (noise filtering, resampling) that Vosk receives, making it perfect for:
- Debugging recognition issues
- Reviewing audio quality
- Training data preparation
- Performance analysis

### **Cross-Platform Audio System Detection**

Automatically detects and reports your audio system:

```bash
vosk-wrapper-1000 daemon --foreground
# Output shows:
# === Audio System Information ===
# Platform: Linux
# Audio System: pipewire
# Audio Backend: pipewire-python / sounddevice
# Details: Pipewire Version, availability, etc.
```

**Supported Systems:**
- **Linux**: PipeWire, PulseAudio, ALSA
- **macOS**: CoreAudio
- **Windows**: WASAPI, DirectSound, MME

## Advanced Recognition Options

Vosk-wrapper-1000 exposes several Vosk recognition parameters:

-   **`--words`**: Enable word-level timestamps in the recognition output. This adds timing information for each recognized word.
-   **`--partial-words`**: Enable partial word results during recognition. Useful for real-time feedback as words are being spoken.
-   **`--grammar "word1 word2 word3"`**: Restrict recognition to a specific vocabulary. This can improve accuracy when you know the expected words (e.g., voice commands like "yes no stop start").

Example:
```bash
# Voice command system with restricted vocabulary
vosk-wrapper-1000 daemon --name commands \
  --grammar "open close start stop yes no cancel" \
  --words \
  --partial-words
```

## Managing Multiple Instances

You can run multiple instances of vosk-wrapper-1000 simultaneously with different models or configurations. Each instance is identified by a unique name:

```bash
# Start multiple instances with different models
vosk-wrapper-1000 daemon --name english --model ~/.local/share/vosk-wrapper-1000/models/vosk-model-en-us-0.22 &
vosk-wrapper-1000 daemon --name german --model ~/.local/share/vosk-wrapper-1000/models/vosk-model-de-0.21 &
vosk-wrapper-1000 daemon --name spanish --model ~/.local/share/vosk-wrapper-1000/models/vosk-model-es-0.42 &

# List all running instances
vosk-wrapper-1000 list

# Control specific instances
vosk-wrapper-1000 start english
vosk-wrapper-1000 stop german
vosk-wrapper-1000 terminate spanish
```

## File Locations

The application follows the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) for portable configuration and data storage:

-   **Models**: `$XDG_DATA_HOME/vosk-wrapper-1000/models/` (default: `~/.local/share/vosk-wrapper-1000/models/`)
-   **Hooks**: `$XDG_CONFIG_HOME/vosk-wrapper-1000/hooks/` (default: `~/.config/vosk-wrapper-1000/hooks/`)
-   **PID Files**: `$XDG_CACHE_HOME/vosk-wrapper-1000/pids/` (default: `~/.cache/vosk-wrapper-1000/pids/`)

You can override these locations using:
-   `XDG_DATA_HOME` environment variable for models
-   `XDG_CONFIG_HOME` environment variable for hooks
-   Command-line arguments: `--model` and `--hooks-dir`

### Example: Using Custom Directories

```bash
# Use custom XDG directories (with installed commands)
XDG_DATA_HOME=~/my-data XDG_CONFIG_HOME=~/my-config vosk-wrapper-1000

# Or use command-line arguments
vosk-wrapper-1000 --model /path/to/model --hooks-dir /path/to/hooks

# When running from source
XDG_DATA_HOME=~/my-data XDG_CONFIG_HOME=~/my-config uvx --from . vosk-wrapper-1000
```

## Controls

The application provides built-in commands for controlling instances:

```bash
# Using built-in commands (recommended)
vosk-wrapper-1000 start [instance-name]     # Start listening
vosk-wrapper-1000 stop [instance-name]      # Stop listening
vosk-wrapper-1000 terminate [instance-name] # Terminate instance
vosk-wrapper-1000 list                      # List all instances
```

You can also manually send signals if needed:

-   **Start Listening**: `SIGUSR1`
-   **Stop Listening**: `SIGUSR2`
-   **Terminate**: `SIGTERM` or `SIGINT` (Ctrl+C)

Example:
```bash
# Get the PID from the PID file
PID=$(cat ~/.cache/vosk-wrapper-1000/pids/default.pid)

# Or find it with pgrep
PID=$(pgrep -f "vosk-wrapper-1000.*--name default")

# Send signals manually
kill -SIGUSR1 $PID  # Start listening
kill -SIGUSR2 $PID  # Stop listening
kill -SIGTERM $PID  # Terminate
```

## Hooks System

The application supports a flexible hook system to react to events. Hooks are executable scripts placed in the hooks directory structure (default: `~/.config/vosk-wrapper-1000/hooks/`).

### Event Types

-   **`hooks/start/`**: Triggered when listening starts.
-   **`hooks/line/`**: Triggered for every transcribed line. The text is passed via `stdin`.
-   **`hooks/stop/`**: Triggered when listening stops.

### JSON Hooks

Hooks with `json` in their filename receive structured JSON data instead of plain text. This is useful for programmatic processing of transcript data.

**JSON Format:**
```json
{
  "type": "transcript",
  "data": "transcribed text content",
  "timestamp": 1640995200.123,
  "event": "line|stop|start"
}
```

**Available JSON Hook Examples:**
- `hooks/start/02_json_logger.sh` - Logs when listening starts
- `hooks/line/03_json_processor.sh` - Processes each transcript line with analysis
- `hooks/stop/02_json_example.sh` - Handles final transcript with session statistics

**Creating a JSON Hook:**
```bash
# Create a JSON hook (note 'json' in filename)
echo '#!/bin/bash' > ~/.config/vosk-wrapper-1000/hooks/line/01_json_processor.sh
echo 'json_data=$(cat)' >> ~/.config/vosk-wrapper-1000/hooks/line/01_json_processor.sh
echo 'echo "Received JSON: $json_data" >&2' >> ~/.config/vosk-wrapper-1000/hooks/line/01_json_processor.sh
chmod +x ~/.config/vosk-wrapper-1000/hooks/line/01_json_processor.sh
```

**JSON Hook Use Cases:**
- Structured logging with timestamps
- Integration with external APIs
- Advanced text analysis and processing
- Session statistics and metrics
- Conditional actions based on transcript content

### Creating Hooks

To create hooks, place executable scripts in the appropriate subdirectories:

```bash
# Create the hooks directory structure
mkdir -p ~/.config/vosk-wrapper-1000/hooks/{start,line,stop}

# Example: Create a hook that runs when listening starts
echo '#!/bin/bash' > ~/.config/vosk-wrapper-1000/hooks/start/01_notify.sh
echo 'echo "Listening started!"' >> ~/.config/vosk-wrapper-1000/hooks/start/01_notify.sh
chmod +x ~/.config/vosk-wrapper-1000/hooks/start/01_notify.sh
```

### Return Codes

Hooks can control the application flow using return codes:

-   **`0`**: Continue normal execution.
-   **`100`**: Request to **stop listening** (valid in `start` and `line` hooks).
-   **`101`**: Request to **terminate** the application immediately.

### Example Hooks

Example scripts are provided in the repository's `hooks/` directory. To use them, copy them to your XDG hooks directory:

```bash
# Clone the repository if you haven't already
git clone https://github.com/rwese/vosk-wrapper-1000-py
cd vosk-wrapper-1000-py

# Copy example hooks to your config directory
cp -r hooks/* ~/.config/vosk-wrapper-1000/hooks/
chmod +x ~/.config/vosk-wrapper-1000/hooks/*/*.sh
chmod +x ~/.config/vosk-wrapper-1000/hooks/*/*.py
```

You can also reference the [repository's `hooks/` directory](https://github.com/rwese/vosk-wrapper-1000-py/tree/main/hooks) for examples of how to write custom hooks.

## Architecture Overview

### **Modular Design (v2.0+)**

The codebase is now organized into focused modules:

```
vosk-wrapper-1000/
├── src/
│   └── vosk_wrapper_1000/
│       ├── __init__.py         # Package initialization
│       ├── main.py             # CLI interface and orchestration
│       ├── audio_processor.py   # soxr resampling + noise filtering
│       ├── audio_recorder.py    # WAV file recording
│       ├── audio_system.py      # Cross-platform audio system detection
│       ├── device_manager.py    # Audio device management
│       ├── model_manager.py     # Vosk model validation
│       ├── signal_manager.py    # Daemon signal handling
│       ├── hook_manager.py      # Hook system execution
│       ├── pid_manager.py       # Process instance management
│       ├── config_manager.py    # Configuration management
│       ├── download_model.py    # Model downloading utility
│       ├── xdg_paths.py        # XDG path utilities
│       └── audio_backend.py    # Audio backend abstraction
├── tests/                    # Test suite
├── config/                   # Default configuration
├── hooks/                    # Example hook scripts
└── pyproject.toml            # Project configuration
```

**Benefits:**
- **Maintainability**: Each module has a single responsibility
- **Testability**: Individual components can be unit tested
- **Extensibility**: Easy to add new features or modify existing ones
- **Debugging**: Issues can be isolated to specific modules

## Troubleshooting

### Audio Device Issues

**Problem: "Invalid sample rate" or "PaErrorCode -9997" error**

This should no longer occur as application automatically uses your device's native sample rate and handles resampling internally. If you still encounter this error:

1. List your audio devices to verify they're detected:
   ```bash
   vosk-wrapper-1000 daemon --list-devices
   ```

2. Check audio system information:
   ```bash
   vosk-wrapper-1000 daemon --foreground
   # Look for "=== Audio System Information ===" section
   ```

3. Try running in foreground mode to see detailed error messages:
   ```bash
   vosk-wrapper-1000 daemon --foreground
   ```

**Problem: No audio input detected**

1. Verify your device is recognized:
   ```bash
   vosk-wrapper-1000 daemon --list-devices
   ```

2. Check device compatibility:
   ```bash
   vosk-wrapper-1000 daemon --foreground --device "Your Device"
   # Look for "Device compatibility:" message
   ```

3. Specify your device explicitly:
   ```bash
   vosk-wrapper-1000 daemon --device "Your Microphone Name"
   # or by ID
   vosk-wrapper-1000 daemon --device 0
   ```

### Audio Quality Issues

**Problem: Poor recognition accuracy**

1. **Adjust noise reduction**:
   ```bash
   # Try stronger noise reduction
   vosk-wrapper-1000 daemon --noise-reduction 0.4

   # Or try non-stationary noise for variable environments
   vosk-wrapper-1000 daemon --non-stationary-noise
   ```

2. **Record and review audio**:
   ```bash
   vosk-wrapper-1000 daemon --record-audio debug.wav
   # Listen to the file to check audio quality
   ```

3. **Check device compatibility**:
   ```bash
   vosk-wrapper-1000 daemon --foreground
   # Look for device compatibility messages
   ```

2. Try running in foreground mode to see detailed error messages:
   ```bash
   vosk-wrapper-1000 daemon --foreground
   ```

**Problem: No audio input detected**

1. Verify your device is recognized:
   ```bash
   vosk-wrapper-1000 daemon --list-devices
   ```

2. Specify your device explicitly:
   ```bash
   vosk-wrapper-1000 daemon --device "Your Microphone Name"
   # or by ID
   vosk-wrapper-1000 daemon --device 0
   ```

### Instance Management Issues

**Problem: "Instance already running" error**

Check if an instance is actually running:
```bash
vosk-wrapper-1000 list
```

If no instances are listed but you get the error, remove the stale PID file:
```bash
rm ~/.cache/vosk-wrapper-1000/pids/default.pid  # or your instance name
```

**Problem: Can't control instance with start/stop commands**

Ensure the instance is running:
```bash
vosk-wrapper-1000 list
```

If the PID is listed but commands fail, the process may have crashed. Terminate and restart:
```bash
vosk-wrapper-1000 terminate instance-name
vosk-wrapper-1000 daemon --name instance-name
```

### Model Issues

**Problem: "Model not found" error**

Download a model first:
```bash
vosk-download-model-1000 --list
vosk-download-model-1000 --name vosk-model-small-en-us-0.15
```

Or specify an explicit model path:
```bash
vosk-wrapper-1000 daemon --model /path/to/your/model
```

### Debugging

Run in foreground mode to see all output:
```bash
vosk-wrapper-1000 daemon --foreground
```

This will show all log messages, errors, and recognition output in real-time.

**Advanced Debugging with Audio Recording:**
```bash
# Record audio to analyze quality issues
vosk-wrapper-1000 daemon --record-audio debug_session.wav --foreground

# Test with different noise reduction settings
vosk-wrapper-1000 daemon --noise-reduction 0.5 --record-audio strong_noise.wav --foreground
vosk-wrapper-1000 daemon --disable-noise-filter --record-audio no_filter.wav --foreground
```

**Performance Monitoring:**
```bash
# Monitor CPU usage with different settings
htop &  # In one terminal
vosk-wrapper-1000 daemon --noise-reduction 0.2 --foreground  # In another
```

## Development

### Setting Up Development Environment

1. **Clone the repository**
    ```bash
    git clone https://github.com/rwese/vosk-wrapper-1000-py
    cd vosk-wrapper-1000-py
    ```

2. **Install in development mode**
    ```bash
    # Using uv (recommended)
    uv pip install -e .

    # Or using pip
    pip install -e .
    ```

3. **Run tests**
    ```bash
    # Run all tests
    uv run python -m pytest

    # Run unit tests only
    uv run python -m pytest tests/unit/

    # Run integration tests only
    uv run python -m pytest tests/integration/

    # Run with coverage
    uv run python -m pytest --cov=src/vosk_wrapper_1000
    ```

4. **Code quality tools**
    ```bash
    # Format code
    uv run black src/ tests/

    # Sort imports
    uv run isort src/ tests/

    # Lint code
    uv run ruff check src/ tests/

    # Type checking
    uv run mypy src/
    ```

### Project Structure

The project follows a clean, modular architecture:

- **`src/vosk_wrapper_1000/`**: Main package with all core functionality
- **`tests/`**: Comprehensive test suite (unit and integration tests)
- **`config/`**: Default configuration files
- **`hooks/`**: Example hook scripts
- **`pyproject.toml`**: Modern Python project configuration

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and ensure tests pass
4. Run code quality tools and fix any issues
5. Submit a pull request

For detailed development guidelines, see [AGENTS.md](AGENTS.md).
