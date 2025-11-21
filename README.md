# Vosk Simple Speech Recognition

A simple, robust, and configurable Python-based speech recognition service using [Vosk](https://alphacephei.com/vosk/).

**Repository**: [github.com/rwese/vosk-wrapper-1000-py](https://github.com/rwese/vosk-wrapper-1000-py)

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

### Alternative: Traditional Setup

If you prefer not to use uv/uvx:

1.  **Install Dependencies**
    The `run.sh` script handles virtual environment creation and dependency installation automatically.
    ```bash
    ./run.sh
    ```
    *Or manually set up the environment:*
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Download a Model**
    ```bash
    # List all available models
    ./venv/bin/python download_model.py

    # Download a specific model
    ./venv/bin/python download_model.py vosk-model-small-en-us-0.15

    # Delete a model
    ./venv/bin/python download_model.py --delete vosk-model-small-en-us-0.15
    ```

3.  **Start the Daemon**
    ```bash
    ./run.sh
    # Or with options:
    ./run.sh --list-devices
    ./run.sh --device "Microphone Name"
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

## Noise Filtering

Vosk-wrapper-1000 includes built-in noise filtering using the **noisereduce** library to improve speech recognition accuracy in noisy environments. The noise filter is **enabled by default** and uses a stationary spectral gating algorithm optimized for low CPU usage.

### How It Works

The noise filter:
- Analyzes incoming audio for background noise patterns
- Applies spectral gating to reduce stationary noise (fans, AC, electrical hum, etc.)
- Processes audio in real-time with minimal latency
- Uses CPU-efficient stateless mode to minimize performance impact

### Disabling Noise Filtering

If you want to disable noise filtering (e.g., in very quiet environments or for debugging):

```bash
# Disable noise filtering
vosk-wrapper-1000 daemon --disable-noise-filter
```

### Performance

The noise filter is optimized for efficiency:
- Uses stateless processing mode for lower CPU usage
- Applied before resampling to minimize computational overhead
- Typically adds only 5-10% CPU overhead on modern processors

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

## Troubleshooting

### Audio Device Issues

**Problem: "Invalid sample rate" or "PaErrorCode -9997" error**

This should no longer occur as the application automatically uses your device's native sample rate and handles resampling internally. If you still encounter this error:

1. List your audio devices to verify they're detected:
   ```bash
   vosk-wrapper-1000 daemon --list-devices
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
