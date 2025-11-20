# Vosk Simple Speech Recognition

A simple, robust, and configurable Python-based speech recognition service using [Vosk](https://alphacephei.com/vosk/).

## Quick Get Started

1.  **Install Dependencies**
    The `run.sh` script handles virtual environment creation and dependency installation automatically.
    ```bash
    ./run.sh
    ```
    *Alternatively, you can manually set up the environment:*
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Download a Model**
    Use the included downloader to fetch a model.
    ```bash
    # List available models
    ./venv/bin/python download_model.py --list

    # Download a specific model (e.g., small English model)
    ./venv/bin/python download_model.py --name vosk-model-small-en-us-0.15
    ```
    *Or simply run it interactively:*
    ```bash
    ./venv/bin/python download_model.py
    ```

3.  **Run the Application**
    ```bash
    ./run.sh
    ```
    *To specify an input device:*
    ```bash
    ./run.sh --list-devices
    ./run.sh --device "Microphone Name"
    ```

## Controls

The application is controlled via system signals:

-   **Start Listening**: `SIGUSR1`
-   **Stop Listening**: `SIGUSR2`
-   **Terminate**: `SIGTERM` or `SIGINT` (Ctrl+C)

Example:
```bash
# Get the PID
PID=$(pgrep -f "main.py")

# Start listening
kill -SIGUSR1 $PID

# Stop listening
kill -SIGUSR2 $PID
```

## Hooks System

The application supports a flexible hook system to react to events. Hooks are executable scripts placed in the `hooks/` directory structure.

### Event Types

-   **`hooks/start/`**: Triggered when listening starts.
-   **`hooks/line/`**: Triggered for every transcribed line. The text is passed via `stdin`.
-   **`hooks/stop/`**: Triggered when listening stops.

### Return Codes

Hooks can control the application flow using return codes:

-   **`0`**: Continue normal execution.
-   **`100`**: Request to **stop listening** (valid in `start` and `line` hooks).
-   **`101`**: Request to **terminate** the application immediately.

### Example Hooks

See the `hooks/` directory for example scripts (`01_example.sh`) demonstrating usage.
