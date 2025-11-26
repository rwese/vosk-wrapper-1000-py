# Configuration Guide

vosk-wrapper-1000 supports configuration through YAML files and environment variables.

## Configuration File Locations

The application looks for configuration files in the following order:

1. `~/.config/vosk-wrapper-1000/config.yaml` (User config - **recommended**)
2. `config/default.yaml` (Project default)

## Creating a User Configuration

Create your personal configuration file:

```bash
mkdir -p ~/.config/vosk-wrapper-1000
```

Then create `~/.config/vosk-wrapper-1000/config.yaml` with your settings:

```yaml
# User configuration for vosk-wrapper-1000

# Model Settings
model:
  # Default model path - specify your preferred model
  path: /Users/yourusername/.local/share/vosk-wrapper-1000/models/vosk-model-en-us-0.42-gigaspeech

# Logging Settings
logging:
  # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
  level: "INFO"

# Audio Settings (optional)
audio:
  # Specific device to use (leave empty for default)
  device: ""

  # Enable noise reduction
  noise_reduction: true

# Recognition Settings (optional)
recognition:
  # Enable word-level timestamps
  words: false

  # Enable partial results
  partial_words: false
```

## Configuration Options

### Model Settings

```yaml
model:
  # Path to your default Vosk model
  path: /path/to/your/model

  # Default model name for downloading
  default_name: "vosk-model-small-en-us-0.15"

  # Auto-download model if not found
  auto_download: false
```

**Model Priority:**
1. User config file (`~/.config/vosk-wrapper-1000/config.yaml`)
2. First model found in `~/.local/share/vosk-wrapper-1000/models/`
3. Default fallback

### Logging Settings

```yaml
logging:
  # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
  level: "INFO"

  # Log file path (leave empty for stderr only)
  file: null

  # Log format
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### Audio Settings

```yaml
audio:
  # Device ID or name substring (empty = default device)
  device: ""

  # Audio block size for recording
  blocksize: 8000

  # Sample rate (auto-detected if null)
  samplerate: null

  # Number of audio channels
  channels: 1

  # Audio data type
  dtype: "int16"

  # Enable noise reduction
  noise_reduction: true
```

### Recognition Settings

```yaml
recognition:
  # Enable word-level timestamps
  words: false

  # Enable partial results
  partial_words: false

  # Grammar for restricted vocabulary (space-separated words)
  grammar: null

  # Maximum alternatives to return
  max_alternatives: 1
```

### Backend Settings

```yaml
# Backend selection
backend:
  # Backend type: vosk, faster-whisper, whisper
  type: vosk

# Vosk-specific options
vosk_options:
  words: false
  partial_words: false
  grammar: null
  max_alternatives: 1

# FasterWhisper-specific options
faster_whisper_options:
  device: cpu           # cpu, cuda, or auto
  compute_type: int8    # int8, int16, float16, float32
  beam_size: 5
  language: null        # Language code (e.g., 'en') or null for auto-detect
  vad_filter: true      # Enable VAD filtering

# Whisper-specific options
whisper_options:
  device: cpu           # cpu or cuda
  language: null        # Language code or null for auto-detect
  temperature: 0.0      # Sampling temperature
  fp16: false           # Use FP16 (auto-enabled for CUDA)
```

## Environment Variables

Configuration can also be set via environment variables (takes precedence over config files):

### Backend
- `VOSK_BACKEND` - Override backend type (vosk, faster-whisper, whisper)

### Model
- `VOSK_MODEL_PATH` - Override default model path
- `VOSK_MODEL_NAME` - Override default model name

### Audio
- `VOSK_AUDIO_DEVICE` - Override audio device
- `VOSK_AUDIO_BLOCKSIZE` - Override block size
- `VOSK_AUDIO_SAMPLERATE` - Override sample rate

### Recognition
- `VOSK_WORDS` - Enable word timestamps (true/false)
- `VOSK_PARTIAL_WORDS` - Enable partial words (true/false)
- `VOSK_GRAMMAR` - Set grammar restriction

### Logging
- `VOSK_LOG_LEVEL` - Set log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- `VOSK_LOG_FILE` - Set log file path

### Service
- `VOSK_INSTANCE_NAME` - Override instance name

## Example: Using Large Model

To use the large gigaspeech model as your default:

1. Download the model if you haven't:
   ```bash
   vosk-download-model-1000 vosk-model-en-us-0.42-gigaspeech
   ```

2. Create your user config:
   ```bash
   cat > ~/.config/vosk-wrapper-1000/config.yaml <<EOF
   # User configuration
   model:
     path: $HOME/.local/share/vosk-wrapper-1000/models/vosk-model-en-us-0.42-gigaspeech

   logging:
     level: "INFO"
   EOF
   ```

3. Verify it works:
   ```bash
   vosk-wrapper-1000 daemon --foreground
   ```

The large model will now be used automatically without specifying `--model` each time!

## Configuration Priority

Settings are applied in this order (later overrides earlier):

1. Default values (hardcoded)
2. Project config file (`config/default.yaml`)
3. User config file (`~/.config/vosk-wrapper-1000/config.yaml`)
4. Environment variables
5. Command-line arguments (highest priority)
