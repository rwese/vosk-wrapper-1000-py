# AGENTS.md - AI Agent Integration Guide

**CRITICAL DOCUMENTATION FOR AI AGENTS INTEGRATING VOSK-WRAPPER-1000**

This document provides **MANDATORY** guidance for AI agents integrating with vosk-wrapper-1000. You **MUST** follow these instructions exactly.

## Development Commands

### Build/Install
```bash
# Install in development mode
uv pip install -e .

# Build wheel
uv build
```

### Testing
```bash
# Run unit tests
python -m pytest tests/unit/

# Run integration tests
python -m pytest tests/integration/

# Run all tests
python -m pytest tests/

# Run individual test files (legacy)
python tests/test_audio.py --device "AnkerWork" --duration 5
python tests/test_full_flow.py
python tests/test_signals.py

# Run workflow tests
./test_workflow.sh
./test_manual.sh
```

## Directory Structure

The vosk-simple project follows a clean, organized structure:

```
vosk-simple/
├── src/                    # Source code
│   └── vosk_simple/       # Main package
│       ├── __init__.py     # Package initialization
│       ├── main.py         # Main entry point
│       ├── audio_*.py      # Audio processing modules
│       ├── config_manager.py # Configuration management
│       ├── model_manager.py # Model management
│       ├── hook_manager.py # Hook system
│       ├── signal_manager.py # Signal handling
│       ├── pid_manager.py  # Process ID management
│       ├── device_manager.py # Audio device management
│       ├── download_model.py # Model downloading
│       └── xdg_paths.py   # XDG path utilities
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   │   ├── test_config_manager.py
│   │   ├── test_xdg_paths.py
│   │   └── test_*.py      # Other unit tests
│   └── integration/       # Integration tests
│       └── test_integration.py
├── config/                # Configuration files
│   └── default.yaml       # Default configuration
├── docs/                  # Documentation
├── examples/              # Example scripts
├── hooks/                 # Hook scripts
│   ├── line/             # Line processing hooks
│   ├── start/            # Start hooks
│   └── stop/             # Stop hooks
├── pyproject.toml         # Project configuration
├── requirements.txt       # Dependencies
├── AGENTS.md             # This file
└── README.md             # Project documentation
```

### Key Directories

- **src/vosk_simple/**: All Python source code organized as a proper package
- **tests/**: Comprehensive test suite separated into unit and integration tests
- **config/**: Configuration files with sensible defaults
- **docs/**: Project documentation and guides
- **examples/**: Example usage scripts and tutorials
- **hooks/**: Hook scripts for extending functionality

### Configuration System

The project uses a hierarchical configuration system:

1. **Default values** in `config/default.yaml`
2. **User config** in `~/.config/vosk-simple/config.yaml`
3. **Environment variables** with `VOSK_` prefix
4. **Command line arguments** (highest priority)

Configuration is managed by `src/vosk_simple/config_manager.py` and supports:
- YAML configuration files
- Environment variable overrides
- Type validation and defaults
- Hot reloading capabilities

### Code Style
- **Imports**: Standard library first, then third-party, then local modules
- **Formatting**: Follow PEP 8, use 4-space indentation
- **Types**: Use type hints for function signatures and class attributes
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Error handling**: Use try/except blocks, print errors to stderr, exit gracefully
- **Audio**: Import sounddevice only inside functions to avoid PortAudio fork issues

## Table of Contents

1. [Core Principles](#core-principles)
2. [Installation](#installation)
3. [Command Structure](#command-structure)
4. [Working with Instances](#working-with-instances)
5. [Audio Configuration](#audio-configuration)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)
8. [Common Patterns](#common-patterns)

---

## Core Principles

### DO NOT Assume - VERIFY ALWAYS

1. **ALWAYS** check if vosk-wrapper-1000 is installed before attempting to use it
2. **ALWAYS** verify a model exists before starting a daemon
3. **ALWAYS** check running instances before starting new ones
4. **NEVER** assume default settings will work for all environments
5. **NEVER** ignore error messages from the tool

### Command Structure is Fixed

The tool uses **EXACTLY** these commands:

```
vosk-wrapper-1000 daemon      # Start a daemon instance
vosk-wrapper-1000 list        # List running instances
vosk-wrapper-1000 start       # Start listening (SIGUSR1)
vosk-wrapper-1000 stop        # Stop listening (SIGUSR2)
vosk-wrapper-1000 terminate   # Terminate instance (SIGTERM)
```

**DO NOT** use `run` - it has been renamed to `daemon`. You **MUST** use `daemon`.

---

## Installation

### MANDATORY Installation Steps

You **MUST** install vosk-wrapper-1000 before any operations:

```bash
# Using uv (RECOMMENDED)
uv tool install git+https://github.com/rwese/vosk-wrapper-1000-py

# Using pip (alternative)
pip install git+https://github.com/rwese/vosk-wrapper-1000-py
```

### Verification

You **MUST** verify installation succeeded:

```bash
vosk-wrapper-1000 --help
```

**IF** this command fails, the tool is **NOT** installed. You **MUST** install it first.

---

## Command Structure

### Model Download - MANDATORY FIRST STEP

You **MUST** download a model before starting any daemon:

```bash
# 1. REQUIRED: List available models
vosk-download-model-1000 --list

# 2. REQUIRED: Download a specific model
vosk-download-model-1000 --name vosk-model-small-en-us-0.15

# 3. VERIFY: Model was downloaded
ls ~/.local/share/vosk-wrapper-1000/models/
```

**DO NOT** proceed without a downloaded model. The daemon **WILL FAIL** without a model.

### Starting a Daemon Instance

You **MUST** use this exact pattern:

```bash
# Basic daemon start (runs in background by default)
vosk-wrapper-1000 daemon

# Named instance (for multiple simultaneous instances)
vosk-wrapper-1000 daemon --name my-instance

# Foreground mode (for debugging - BLOCKS until terminated)
vosk-wrapper-1000 daemon --foreground

# With specific model
vosk-wrapper-1000 daemon --model ~/.local/share/vosk-wrapper-1000/models/vosk-model-en-us-0.22
```

**CRITICAL**:
- Default behavior is daemon (background) mode
- Use `--foreground` ONLY for debugging
- Each instance **REQUIRES** a unique name if running multiple instances
- The daemon **WILL NOT** listen automatically - you **MUST** send `start` command

### Listing Instances

You **MUST** check running instances before starting new ones:

```bash
vosk-wrapper-1000 list
```

**Expected output:**
```
Name                 PID
------------------------------
default              12345
my-instance          12346
```

**IF** output shows "No running instances found", no daemons are running.

### Controlling Instances

You **MUST** use these exact commands:

```bash
# Start listening (sends SIGUSR1)
vosk-wrapper-1000 start [instance-name]

# Stop listening (sends SIGUSR2)
vosk-wrapper-1000 stop [instance-name]

# Terminate daemon (sends SIGTERM)
vosk-wrapper-1000 terminate [instance-name]
```

**CRITICAL NOTES:**
- Instance name **DEFAULTS** to "default" if not specified
- You **MUST** use the exact instance name from `list` command
- `start` and `stop` control listening state - they do **NOT** start/stop the daemon
- `terminate` stops the daemon completely

---

## Working with Instances

### Instance Lifecycle - MANDATORY SEQUENCE

You **MUST** follow this exact sequence:

```bash
# 1. REQUIRED: Start daemon
vosk-wrapper-1000 daemon --name test

# 2. REQUIRED: Verify it's running
vosk-wrapper-1000 list

# 3. REQUIRED: Start listening
vosk-wrapper-1000 start test

# 4. (Recognition happens here - output goes to stdout)

# 5. REQUIRED: Stop listening when done
vosk-wrapper-1000 stop test

# 6. REQUIRED: Terminate daemon when finished
vosk-wrapper-1000 terminate test
```

**DO NOT** skip steps. **DO NOT** change order.

### Multiple Instances

You **CAN** run multiple instances simultaneously. You **MUST**:

1. Give each instance a **UNIQUE** name
2. Use different models if desired (optional)
3. Track instance names for control commands

```bash
# Start multiple instances
vosk-wrapper-1000 daemon --name english --model ~/.local/share/vosk-wrapper-1000/models/vosk-model-en-us-0.22
vosk-wrapper-1000 daemon --name german --model ~/.local/share/vosk-wrapper-1000/models/vosk-model-de-0.21

# Control them independently
vosk-wrapper-1000 start english
vosk-wrapper-1000 start german

vosk-wrapper-1000 stop english
vosk-wrapper-1000 terminate german
```

**WARNING**: Each instance consumes significant memory (1-5GB depending on model).

---

## Audio Configuration

### Automatic Sample Rate Handling - NO ACTION REQUIRED

The tool **AUTOMATICALLY**:
- Detects your audio device's native sample rate
- Reads the model's required sample rate from configuration
- Performs real-time resampling between rates

You **DO NOT** need to specify `--samplerate` unless overriding.

### Device Selection

You **SHOULD** list available devices first:

```bash
vosk-wrapper-1000 daemon --list-devices
```

**Expected output:**
```
ID   Name                          Channels   Sample Rate
----------------------------------------------------------
0    Built-in Microphone           2 in       48000 Hz
1    USB Webcam                    2 in       48000 Hz
```

Then specify device:

```bash
# By name (substring match)
vosk-wrapper-1000 daemon --device "USB Webcam"

# By ID
vosk-wrapper-1000 daemon --device 0
```

**IF** you do **NOT** specify a device, the system default is used.

### Advanced Recognition Options

You **MAY** use these options:

```bash
# Enable word-level timestamps
vosk-wrapper-1000 daemon --words

# Enable partial results during recognition
vosk-wrapper-1000 daemon --partial-words

# Restrict vocabulary (improves accuracy for known words)
vosk-wrapper-1000 daemon --grammar "yes no stop start cancel"
```

**USE** `--grammar` when you know the expected vocabulary. **DO NOT** use it for general transcription.

---

## Error Handling

### MANDATORY Error Checks

You **MUST** check for these errors and handle them:

#### 1. Instance Already Running

```bash
Error: Instance 'default' is already running with PID 12345
```

**ACTION REQUIRED:**
```bash
# Check if it's actually running
vosk-wrapper-1000 list

# If listed, terminate it first
vosk-wrapper-1000 terminate default

# If NOT listed, remove stale PID file
rm ~/.cache/vosk-wrapper-1000/pids/default.pid
```

#### 2. Model Not Found

```bash
Model not found at '...'
```

**ACTION REQUIRED:**
```bash
# Download a model first
vosk-download-model-1000 --name vosk-model-small-en-us-0.15
```

#### 3. No Running Instance

```bash
Error: No running instance found with name 'test'
```

**ACTION REQUIRED:**
```bash
# Verify instance name
vosk-wrapper-1000 list

# Start the daemon if not running
vosk-wrapper-1000 daemon --name test
```

#### 4. Audio Device Error

```bash
Error starting stream: ...
```

**ACTION REQUIRED:**
```bash
# List available devices
vosk-wrapper-1000 daemon --list-devices

# Specify a valid device
vosk-wrapper-1000 daemon --device "Device Name"
```

### Error Handling Pattern

You **MUST** use this pattern:

```bash
# Attempt operation
if ! vosk-wrapper-1000 daemon 2>&1 | grep -q "Error"; then
    echo "Success: Daemon started"
else
    echo "Error: Check error message and take corrective action"
    # Handle error based on message
fi
```

---

## Best Practices

### DO - Recommended Actions

1. **DO** use named instances for better tracking
2. **DO** check `list` before starting new instances
3. **DO** use `--foreground` during development/debugging
4. **DO** terminate instances when done to free resources
5. **DO** use `--grammar` when vocabulary is known
6. **DO** verify models are downloaded before starting
7. **DO** handle errors explicitly

### DO NOT - Prohibited Actions

1. **DO NOT** assume instances are running - always check with `list`
2. **DO NOT** use `run` command - it's `daemon` now
3. **DO NOT** skip model download step
4. **DO NOT** start multiple instances with the same name
5. **DO NOT** ignore error messages
6. **DO NOT** use `--samplerate` unless you know what you're doing
7. **DO NOT** forget to terminate instances when done

---

## Common Patterns

### Pattern 1: Simple Transcription

```bash
# 1. Download model (once)
vosk-download-model-1000 --name vosk-model-small-en-us-0.15

# 2. Start daemon
vosk-wrapper-1000 daemon

# 3. Start listening
vosk-wrapper-1000 start

# 4. (Speak into microphone - output goes to stdout)

# 5. Stop listening
vosk-wrapper-1000 stop

# 6. Terminate
vosk-wrapper-1000 terminate
```

### Pattern 2: Voice Command Detection

```bash
# Start with restricted vocabulary
vosk-wrapper-1000 daemon --name commands \
  --grammar "open close start stop yes no cancel" \
  --words

# Start listening
vosk-wrapper-1000 start commands

# Process output for command detection
# (Output will only contain the specified words)

# Stop and terminate when done
vosk-wrapper-1000 stop commands
vosk-wrapper-1000 terminate commands
```

### Pattern 3: Multiple Language Support

```bash
# Download models for each language
vosk-download-model-1000 --name vosk-model-en-us-0.22
vosk-download-model-1000 --name vosk-model-de-0.21
vosk-download-model-1000 --name vosk-model-es-0.42

# Start separate instances
vosk-wrapper-1000 daemon --name english \
  --model ~/.local/share/vosk-wrapper-1000/models/vosk-model-en-us-0.22

vosk-wrapper-1000 daemon --name german \
  --model ~/.local/share/vosk-wrapper-1000/models/vosk-model-de-0.21

# Control independently
vosk-wrapper-1000 start english
# (English recognition happens)
vosk-wrapper-1000 stop english

vosk-wrapper-1000 start german
# (German recognition happens)
vosk-wrapper-1000 stop german
```

### Pattern 4: Continuous Monitoring with Hooks

```bash
# Create hook directory structure
mkdir -p ~/.config/vosk-wrapper-1000/hooks/{start,line,stop}

# Create a line hook to process each transcribed line
cat > ~/.config/vosk-wrapper-1000/hooks/line/01_process.sh << 'EOF'
#!/bin/bash
# $1 = current line
# stdin = full transcript so far

echo "Transcribed: $1" >> /tmp/transcription.log
EOF

chmod +x ~/.config/vosk-wrapper-1000/hooks/line/01_process.sh

# Start daemon with hooks enabled
vosk-wrapper-1000 daemon
vosk-wrapper-1000 start

# Hooks will process each line automatically
```

---

## File Locations - IMPORTANT

You **MUST** know these paths:

### Configuration
```
~/.config/vosk-wrapper-1000/hooks/     # Hook scripts
```

### Data
```
~/.local/share/vosk-wrapper-1000/models/   # Downloaded models
```

### Runtime
```
~/.cache/vosk-wrapper-1000/pids/          # PID files for instances
```

### Override via Environment

You **CAN** override paths:

```bash
XDG_CONFIG_HOME=/custom/config vosk-wrapper-1000 daemon
XDG_DATA_HOME=/custom/data vosk-wrapper-1000 daemon
XDG_CACHE_HOME=/custom/cache vosk-wrapper-1000 daemon
```

---

## Debugging

### Debug Mode - Foreground Execution

You **MUST** use foreground mode for debugging:

```bash
vosk-wrapper-1000 daemon --foreground
```

**CRITICAL**: This command **BLOCKS** until terminated. You **MUST** run it in a separate terminal or background it manually.

### Log Output

All logs go to **stderr**. Recognition output goes to **stdout**.

You **MUST** separate them:

```bash
# Capture logs only
vosk-wrapper-1000 daemon --foreground 2> daemon.log

# Capture recognition only
vosk-wrapper-1000 daemon --foreground > recognition.txt 2> /dev/null

# Capture both separately
vosk-wrapper-1000 daemon --foreground > recognition.txt 2> daemon.log
```

---

## Integration Checklist

Before integrating vosk-wrapper-1000, you **MUST** complete this checklist:

- [ ] Tool is installed (`vosk-wrapper-1000 --help` works)
- [ ] Model downloader is available (`vosk-download-model-1000 --help` works)
- [ ] At least one model is downloaded
- [ ] Audio device is detected (`vosk-wrapper-1000 daemon --list-devices`)
- [ ] Test daemon can start successfully
- [ ] Test control commands work (start/stop/terminate)
- [ ] Test instance listing works
- [ ] Error handling is implemented for all commands
- [ ] Cleanup (terminate) is called when done

**IF** any checklist item fails, you **MUST** resolve it before proceeding.

---

## Support and Resources

- **Repository**: https://github.com/rwese/vosk-wrapper-1000-py
- **Model List**: https://alphacephei.com/vosk/models
- **Vosk Documentation**: https://alphacephei.com/vosk/

---

## Final Notes

This tool is **PRODUCTION-READY** but requires **CORRECT USAGE**. Follow this guide **EXACTLY**.

**DO NOT**:
- Deviate from documented commands
- Skip prerequisite steps
- Ignore error messages
- Assume defaults will work everywhere

**DO**:
- Verify each step
- Handle errors explicitly
- Clean up resources (terminate instances)
- Test in foreground mode first

**Remember**: This is a daemon-based service. You **MUST** manage the lifecycle properly: start daemon → start listening → stop listening → terminate daemon.
