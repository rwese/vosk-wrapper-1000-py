# Homebrew Installation and Tap Guide

This guide explains how to install vosk-wrapper-1000 using Homebrew on macOS and Linux.

## Quick Start

### Install from Homebrew Tap

```bash
# Add the tap (one-time setup)
brew tap rwese/vosk-wrapper-1000 https://github.com/rwese/vosk-wrapper-1000-py

# Install vosk-wrapper-1000
brew install vosk-wrapper-1000

# Download a Vosk model
vosk-download-model-1000 vosk-model-small-en-us-0.15

# Run the daemon
vosk-wrapper-1000 daemon
```

## Installation Options

### Option 1: Install from Tap (Recommended)

```bash
# Add tap
brew tap rwese/vosk-wrapper-1000 https://github.com/rwese/vosk-wrapper-1000-py

# Install
brew install vosk-wrapper-1000

# Update
brew upgrade vosk-wrapper-1000

# Uninstall
brew uninstall vosk-wrapper-1000
brew untap rwese/vosk-wrapper-1000
```

### Option 2: Install Directly from URL

```bash
# Install without adding tap
brew install https://raw.githubusercontent.com/rwese/vosk-wrapper-1000-py/main/Formula/vosk-wrapper-1000.rb

# Update (requires URL again)
brew reinstall https://raw.githubusercontent.com/rwese/vosk-wrapper-1000-py/main/Formula/vosk-wrapper-1000.rb
```

### Option 3: Install from Local Formula

```bash
# Clone the repository
git clone https://github.com/rwese/vosk-wrapper-1000-py
cd vosk-wrapper-1000-py

# Install from local formula
brew install --build-from-source Formula/vosk-wrapper-1000.rb
```

## Running as a Service

Homebrew can manage vosk-wrapper-1000 as a background service:

### Start Service

```bash
# Start service (runs in background)
brew services start vosk-wrapper-1000

# Check service status
brew services info vosk-wrapper-1000

# View service logs
tail -f $(brew --prefix)/var/log/vosk-wrapper-1000.log
```

### Stop Service

```bash
# Stop service
brew services stop vosk-wrapper-1000

# Restart service
brew services restart vosk-wrapper-1000
```

### Service Configuration

The Homebrew service runs with these settings:
- **Command**: `vosk-wrapper-1000 daemon --name default --foreground`
- **Log file**: `$(brew --prefix)/var/log/vosk-wrapper-1000.log`
- **Error log**: `$(brew --prefix)/var/log/vosk-wrapper-1000-error.log`
- **Auto-restart**: Yes (service keeps running)

## File Locations

### Homebrew Installation Paths

```bash
# Installation prefix
brew --prefix vosk-wrapper-1000
# Example: /usr/local/opt/vosk-wrapper-1000 (Intel Mac)
# Example: /opt/homebrew/opt/vosk-wrapper-1000 (Apple Silicon)

# Executables
$(brew --prefix)/bin/vosk-wrapper-1000
$(brew --prefix)/bin/vosk-download-model-1000
$(brew --prefix)/bin/vosk-transcribe-file
$(brew --prefix)/bin/vosk-settings-tui

# Models directory
$(brew --prefix)/var/lib/vosk-wrapper-1000/models

# Configuration
$(brew --prefix)/etc/vosk-wrapper-1000
```

### User Configuration Paths

```bash
# User config (XDG standard)
~/.config/vosk-wrapper-1000/config.yaml

# User models
~/.local/share/vosk-wrapper-1000/models

# User cache
~/.cache/vosk-wrapper-1000
```

## Post-Installation Setup

### Download a Model

After installation, download at least one Vosk model:

```bash
# List available models
vosk-download-model-1000

# Download small English model (recommended for testing)
vosk-download-model-1000 vosk-model-small-en-us-0.15

# Download larger, more accurate model
vosk-download-model-1000 vosk-model-en-us-0.22
```

Models are stored in:
- System: `$(brew --prefix)/var/lib/vosk-wrapper-1000/models`
- User: `~/.local/share/vosk-wrapper-1000/models`

### Configure Audio Settings

Use the interactive TUI to configure audio settings:

```bash
vosk-settings-tui
```

Or manually create/edit configuration:

```bash
mkdir -p ~/.config/vosk-wrapper-1000
cat > ~/.config/vosk-wrapper-1000/config.yaml <<EOF
model:
  path: ~/.local/share/vosk-wrapper-1000/models/vosk-model-small-en-us-0.15

audio:
  noise_reduction_enabled: true
  noise_reduction_level: 0.2

logging:
  level: INFO
EOF
```

## Usage Examples

### Basic Usage

```bash
# Run daemon in foreground (for testing)
vosk-wrapper-1000 daemon --foreground

# Run daemon in background
vosk-wrapper-1000 daemon

# List running instances
vosk-wrapper-1000 list

# Start listening
vosk-wrapper-1000 start

# Stop listening
vosk-wrapper-1000 stop

# Terminate daemon
vosk-wrapper-1000 terminate
```

### Using with Homebrew Services

```bash
# Start as service (auto-starts on boot)
brew services start vosk-wrapper-1000

# Control via IPC
vosk-wrapper-1000 send toggle
vosk-wrapper-1000 send status

# Stream transcriptions
vosk-wrapper-1000 stream

# View logs
tail -f $(brew --prefix)/var/log/vosk-wrapper-1000.log
```

### Transcribe Audio Files

```bash
# Transcribe a file
vosk-transcribe-file audio.wav

# Save to file
vosk-transcribe-file audio.mp3 --output transcript.txt

# Use specific model
vosk-transcribe-file audio.wav --model ~/.local/share/vosk-wrapper-1000/models/vosk-model-en-us-0.22
```

## Troubleshooting

### Command Not Found

If commands aren't found after installation:

```bash
# Check if installed
brew list vosk-wrapper-1000

# Verify PATH
echo $PATH | grep $(brew --prefix)/bin

# Add to PATH if needed (add to ~/.zshrc or ~/.bash_profile)
export PATH="$(brew --prefix)/bin:$PATH"
```

### Service Won't Start

```bash
# Check service status
brew services info vosk-wrapper-1000

# View error logs
cat $(brew --prefix)/var/log/vosk-wrapper-1000-error.log

# Try running manually to see errors
vosk-wrapper-1000 daemon --foreground

# Restart service
brew services restart vosk-wrapper-1000
```

### Permission Issues

```bash
# Ensure directories exist
mkdir -p ~/.local/share/vosk-wrapper-1000/models
mkdir -p ~/.config/vosk-wrapper-1000
mkdir -p ~/.cache/vosk-wrapper-1000

# Fix permissions
chmod 755 ~/.local/share/vosk-wrapper-1000
chmod 755 ~/.config/vosk-wrapper-1000
```

### Model Not Found

```bash
# Check model locations
ls -la ~/.local/share/vosk-wrapper-1000/models/
ls -la $(brew --prefix)/var/lib/vosk-wrapper-1000/models/

# Download a model
vosk-download-model-1000 vosk-model-small-en-us-0.15

# Specify model explicitly
vosk-wrapper-1000 daemon --model ~/.local/share/vosk-wrapper-1000/models/vosk-model-small-en-us-0.15
```

### Updating

```bash
# Update Homebrew
brew update

# Upgrade vosk-wrapper-1000
brew upgrade vosk-wrapper-1000

# If service is running, restart it
brew services restart vosk-wrapper-1000
```

## Development Installation

For development or testing unreleased versions:

```bash
# Install HEAD (latest main branch)
brew install --HEAD vosk-wrapper-1000

# Install with build options
brew install --build-from-source vosk-wrapper-1000

# Reinstall (force rebuild)
brew reinstall vosk-wrapper-1000
```

## Uninstallation

### Complete Uninstallation

```bash
# Stop service if running
brew services stop vosk-wrapper-1000

# Uninstall package
brew uninstall vosk-wrapper-1000

# Remove tap
brew untap rwese/vosk-wrapper-1000

# Remove user data (optional)
rm -rf ~/.local/share/vosk-wrapper-1000
rm -rf ~/.config/vosk-wrapper-1000
rm -rf ~/.cache/vosk-wrapper-1000

# Remove Homebrew data (optional)
rm -rf $(brew --prefix)/var/lib/vosk-wrapper-1000
rm -rf $(brew --prefix)/var/log/vosk-wrapper-1000*.log
```

## Creating Your Own Tap

If you want to create a custom tap for vosk-wrapper-1000:

### Step 1: Create Tap Repository

```bash
# Create a new repository named homebrew-<tap-name>
# Example: homebrew-vosk-wrapper-1000

# Clone it locally
git clone https://github.com/yourusername/homebrew-vosk-wrapper-1000
cd homebrew-vosk-wrapper-1000
```

### Step 2: Add Formula

```bash
# Create Formula directory
mkdir -p Formula

# Copy the formula
cp /path/to/vosk-wrapper-1000-py/Formula/vosk-wrapper-1000.rb Formula/

# Commit and push
git add Formula/vosk-wrapper-1000.rb
git commit -m "Add vosk-wrapper-1000 formula"
git push
```

### Step 3: Update SHA256

```bash
# Generate tarball
git archive --format=tar.gz --output=vosk-wrapper-1000-0.1.0.tar.gz --prefix=vosk-wrapper-1000-0.1.0/ v0.1.0

# Calculate SHA256
shasum -a 256 vosk-wrapper-1000-0.1.0.tar.gz

# Update formula with the SHA256
```

### Step 4: Test Formula

```bash
# Test installation
brew install --build-from-source Formula/vosk-wrapper-1000.rb

# Run tests
brew test vosk-wrapper-1000

# Audit formula
brew audit --strict vosk-wrapper-1000
```

### Step 5: Use Your Tap

```bash
# Users can now install from your tap
brew tap yourusername/vosk-wrapper-1000
brew install vosk-wrapper-1000
```

## See Also

- [Main README](../README.md) - General documentation
- [Systemd Service Setup](SYSTEMD_SERVICE.md) - Linux service setup
- [Configuration Guide](CONFIGURATION.md) - Configuration options
- [Homebrew Documentation](https://docs.brew.sh/) - Official Homebrew docs
