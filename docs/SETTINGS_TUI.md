# Settings TUI - Interactive Audio Configuration

The Settings TUI (`vosk-settings-tui`) provides an interactive terminal interface for experimenting with audio processing settings in real-time.

## Features

- 🎚️ **Visual Controls**: Adjust all audio processing parameters with an intuitive interface
- 💾 **Config Management**: Save settings directly to your config file
- 🔄 **Live Updates**: See how different settings affect your audio processing
- 📊 **Organized Sections**: Settings grouped by category (Noise Reduction, Audio Gate, Normalization)
- ⌨️ **Keyboard Navigation**: Efficient keyboard shortcuts for all actions

## Installation

The TUI is included with vosk-wrapper-1000. Make sure you have the latest version installed:

```bash
uv sync  # If developing
# or
pip install vosk-wrapper-1000  # If using released version
```

## Usage

### Launch the TUI

```bash
# Use default config location (~/.config/vosk-wrapper-1000/config.yaml)
vosk-settings-tui

# Specify a custom config file
vosk-settings-tui --config /path/to/custom/config.yaml
```

### Navigation

- **Tab / Shift+Tab**: Move between controls
- **Enter**: Toggle checkboxes or edit inputs
- **Arrow Keys**: Navigate through settings
- **Scroll**: Use mouse wheel or Page Up/Down to scroll

### Keyboard Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| `S` | Save | Save current settings to config file |
| `R` | Reset | Reset to default values |
| `T` | Test | Test current settings (shows command to run) |
| `Q` | Quit | Exit the TUI |

## Settings Reference

### 🎚️ Noise Reduction

Configure noise filtering and reduction algorithms.

#### Enable Noise Reduction
- **Type**: Boolean (checkbox)
- **Default**: `True`
- **Description**: Master switch for noise reduction processing

#### Noise Reduction Level
- **Type**: Float (0.0-1.0)
- **Default**: `0.05`
- **Description**: Controls how aggressive the noise reduction is
  - `0.0`: No reduction (pass-through)
  - `0.05`: Light reduction (default, preserves speech quality)
  - `0.3`: Moderate reduction (good for noisy environments)
  - `1.0`: Maximum reduction (may affect speech quality)

#### Stationary Noise Mode
- **Type**: Boolean (checkbox)
- **Default**: `False` (uses non-stationary mode)
- **Description**: Choose noise reduction algorithm
  - **Unchecked (Non-stationary)**: Adapts to changing noise (office, outdoor)
  - **Checked (Stationary)**: Faster, for constant noise (fan, AC hum)

#### Min RMS Ratio
- **Type**: Float (0.0-1.0)
- **Default**: `0.5`
- **Description**: Prevents over-aggressive noise reduction
  - If noise reduction reduces volume below this ratio, it's skipped
  - Higher values = more conservative reduction
  - Lower values = allow more aggressive reduction

### 🚪 Audio Gate (Voice Activity Detection)

Control when audio is processed based on volume and silence detection.

#### Silence Threshold
- **Type**: Float (RMS value)
- **Default**: `50.0`
- **Description**: Audio below this energy level is considered silence
  - Higher values = less sensitive (only loud sounds trigger gate)
  - Lower values = more sensitive (quiet sounds trigger gate)
  - Typical range: `20.0` to `100.0`

#### VAD Hysteresis Chunks
- **Type**: Integer
- **Default**: `10`
- **Description**: Number of consecutive silent chunks before gate closes
  - Prevents gate from closing during natural speech pauses
  - Higher values = allow longer pauses in speech
  - Each chunk is typically ~64ms (depends on blocksize)
  - `10` chunks ≈ 640ms pause tolerance

#### Pre-roll Duration
- **Type**: Float (seconds)
- **Default**: `2.0`
- **Description**: Duration of audio captured before speech detection
  - Prevents cutting off the beginning of words
  - Maintains a ring buffer of this duration
  - Higher values = more memory usage but better word capture
  - Recommended range: `1.0` to `3.0` seconds

### 📊 Audio Normalization

Adjust audio levels before processing.

#### Enable Normalization
- **Type**: Boolean (checkbox)
- **Default**: `False`
- **Description**: Automatically adjust audio volume to target level
  - Useful for quiet microphones
  - Helps maintain consistent volume across recordings

#### Target Level
- **Type**: Float (0.0-1.0)
- **Default**: `0.3`
- **Description**: Target RMS level for normalized audio
  - `0.1`: Quiet output
  - `0.3`: Moderate output (default)
  - `0.7`: Loud output
  - Maximum gain is capped at 10x to prevent distortion

## Workflow

### Typical Experimentation Workflow

1. **Launch TUI**:
   ```bash
   vosk-settings-tui
   ```

2. **Adjust Settings**: Use Tab to navigate, Enter to edit values

3. **Save Settings**: Press `S` or click "Save Settings" button

4. **Test with Daemon**:
   ```bash
   # Start daemon with new settings (reads from config file)
   vosk-daemon --record-audio ~/test-audio.wav

   # Start listening
   vosk-start

   # Speak into microphone...

   # Stop and check recording
   vosk-stop
   vosk-terminate

   # Listen to recorded audio
   ffplay ~/test-audio.wav
   ```

5. **Iterate**: Return to TUI, adjust settings, save, and test again

### Quick Testing Different Scenarios

#### Quiet Microphone
```
Enable Normalization: ✓
Target Level: 0.5
Noise Reduction Level: 0.05
```

#### Noisy Office Environment
```
Noise Reduction Level: 0.3
Stationary Noise Mode: ☐ (non-stationary)
Silence Threshold: 80.0
```

#### Constant Fan Noise
```
Noise Reduction Level: 0.2
Stationary Noise Mode: ✓
Silence Threshold: 50.0
```

#### Sensitive Gate (Capture Whispers)
```
Silence Threshold: 20.0
VAD Hysteresis Chunks: 15
Pre-roll Duration: 3.0
```

## Configuration File Format

Settings are saved to `~/.config/vosk-wrapper-1000/config.yaml`:

```yaml
audio:
  noise_reduction_enabled: true
  noise_reduction_level: 0.05
  stationary_noise: false
  silence_threshold: 50.0
  normalize_audio: false
  normalization_target_level: 0.3
  vad_hysteresis_chunks: 10
  pre_roll_duration: 0.5
  noise_reduction_min_rms_ratio: 0.5
```

## Troubleshooting

### TUI doesn't start
- Ensure textual is installed: `uv sync` or `pip install textual>=0.47.0`
- Check Python version: Requires Python 3.8+

### Settings not applying
- Make sure you pressed `S` to save before exiting
- Verify config file location: Check subtitle in TUI header
- Restart vosk-daemon after changing settings

### Can't edit input fields
- Press `Enter` to focus/edit an input field
- Press `Enter` again to confirm changes
- Use `Esc` to cancel editing

## Tips and Best Practices

1. **Start Conservative**: Begin with default values and make small adjustments
2. **Test Incrementally**: Change one setting at a time to understand its impact
3. **Record Test Audio**: Always use `--record-audio` to verify what Vosk receives
4. **Monitor RMS Values**: Use audio analysis tools to understand your microphone's typical RMS levels
5. **Environment-Specific**: Save different configs for different environments (home, office, etc.)

## Advanced Usage

### Multiple Config Files

```bash
# Create environment-specific configs
vosk-settings-tui --config ~/.config/vosk-wrapper-1000/config-office.yaml
vosk-settings-tui --config ~/.config/vosk-wrapper-1000/config-home.yaml

# Use specific config with daemon
vosk-daemon --config ~/.config/vosk-wrapper-1000/config-office.yaml
```

### Programmatic Access

The TUI reads and writes standard YAML config files, so you can also edit them directly:

```python
import yaml
from pathlib import Path

config_path = Path.home() / ".config/vosk-wrapper-1000/config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

# Modify settings
config["audio"]["noise_reduction_level"] = 0.15

with open(config_path, "w") as f:
    yaml.dump(config, f)
```

## See Also

- [Audio Processing Pipeline](./AUDIO_PROCESSING.md)
- [Configuration Guide](./CONFIGURATION.md)
- [Daemon CLI Reference](../README.md#daemon-mode)
