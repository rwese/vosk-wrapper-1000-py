# Systemd User Service Setup

This guide explains how to set up vosk-wrapper-1000 as a systemd user service on Linux, allowing it to run automatically in the background and start on login.

## Quick Start

### Install and Enable Service

```bash
# Install, enable, and start the default service
./scripts/setup-systemd-service.sh --enable --start

# Install named instance
./scripts/setup-systemd-service.sh --name my-mic --enable --start
```

### Basic Service Management

```bash
# Start service
systemctl --user start vosk-wrapper-1000-default.service

# Stop service
systemctl --user stop vosk-wrapper-1000-default.service

# Check status
systemctl --user status vosk-wrapper-1000-default.service

# View logs
journalctl --user -u vosk-wrapper-1000-default.service -f
```

## Installation Methods

### Method 1: Using Setup Script (Recommended)

The setup script automates the entire installation process:

```bash
# Basic installation (creates service but doesn't enable/start)
./scripts/setup-systemd-service.sh

# Install and enable (start on boot)
./scripts/setup-systemd-service.sh --enable

# Install, enable, and start immediately
./scripts/setup-systemd-service.sh --enable --start

# Install named instance
./scripts/setup-systemd-service.sh --name work-mic --enable --start
```

**Script Options:**
- `-n, --name NAME` - Instance name (default: default)
- `-e, --enable` - Enable service to start on boot
- `-s, --start` - Start service immediately
- `-u, --uninstall` - Uninstall the service
- `-h, --help` - Show help message

### Method 2: Manual Installation

If you prefer manual installation:

```bash
# Create systemd user directory
mkdir -p ~/.config/systemd/user

# Copy service file (for default instance)
cp systemd/vosk-wrapper-1000-default.service ~/.config/systemd/user/

# Or for named instances, copy and edit the template
cp systemd/vosk-wrapper-1000@.service ~/.config/systemd/user/vosk-wrapper-1000@my-instance.service

# Reload systemd
systemctl --user daemon-reload

# Enable and start
systemctl --user enable vosk-wrapper-1000-default.service
systemctl --user start vosk-wrapper-1000-default.service
```

## Service Management

### Start/Stop/Restart

```bash
# Start service
systemctl --user start vosk-wrapper-1000-default.service

# Stop service
systemctl --user stop vosk-wrapper-1000-default.service

# Restart service
systemctl --user restart vosk-wrapper-1000-default.service

# Reload configuration without restart
systemctl --user reload-or-restart vosk-wrapper-1000-default.service
```

### Enable/Disable Auto-start

```bash
# Enable service to start on login
systemctl --user enable vosk-wrapper-1000-default.service

# Disable auto-start
systemctl --user disable vosk-wrapper-1000-default.service

# Check if enabled
systemctl --user is-enabled vosk-wrapper-1000-default.service
```

### Check Status

```bash
# Check service status
systemctl --user status vosk-wrapper-1000-default.service

# Check if service is running
systemctl --user is-active vosk-wrapper-1000-default.service
```

## Viewing Logs

### Real-time Logs

```bash
# Follow logs (like tail -f)
journalctl --user -u vosk-wrapper-1000-default.service -f

# Follow logs with timestamps
journalctl --user -u vosk-wrapper-1000-default.service -f -o short-iso
```

### Historical Logs

```bash
# Last 50 lines
journalctl --user -u vosk-wrapper-1000-default.service -n 50

# Since yesterday
journalctl --user -u vosk-wrapper-1000-default.service --since yesterday

# Since specific time
journalctl --user -u vosk-wrapper-1000-default.service --since "2025-11-25 10:00:00"

# Between time ranges
journalctl --user -u vosk-wrapper-1000-default.service --since "2025-11-25 10:00" --until "2025-11-25 11:00"
```

### Log Filtering

```bash
# Show only errors
journalctl --user -u vosk-wrapper-1000-default.service -p err

# Show warnings and errors
journalctl --user -u vosk-wrapper-1000-default.service -p warning

# Grep for specific text
journalctl --user -u vosk-wrapper-1000-default.service | grep "transcription"
```

## Multiple Instances

You can run multiple instances with different configurations:

```bash
# Install multiple instances
./scripts/setup-systemd-service.sh --name english --enable --start
./scripts/setup-systemd-service.sh --name german --enable --start
./scripts/setup-systemd-service.sh --name work-mic --enable --start

# Manage them independently
systemctl --user start vosk-wrapper-1000-english.service
systemctl --user stop vosk-wrapper-1000-german.service
systemctl --user status vosk-wrapper-1000-work-mic.service

# View logs for specific instance
journalctl --user -u vosk-wrapper-1000-english.service -f
```

## Configuration

### Customizing Service File

If you need custom settings (different model, device, etc.), edit the service file:

```bash
# Edit service file
$EDITOR ~/.config/systemd/user/vosk-wrapper-1000-default.service

# Example: Use specific model and device
ExecStart=/home/user/.local/bin/vosk-wrapper-1000 daemon \
  --name default \
  --foreground \
  --model /path/to/model \
  --device "USB Microphone" \
  --webrtc-enabled

# Reload and restart after changes
systemctl --user daemon-reload
systemctl --user restart vosk-wrapper-1000-default.service
```

### Environment Variables

Add environment variables to the service:

```bash
# Edit service file
[Service]
Environment="VOSK_LOG_LEVEL=INFO"
Environment="VOSK_IPC_ENABLED=true"
Environment="VOSK_WEBRTC_ENABLED=true"
ExecStart=/home/user/.local/bin/vosk-wrapper-1000 daemon --name default --foreground
```

### Resource Limits

The default service includes security hardening and resource limits:

```ini
# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=%h/.local/share/vosk-wrapper-1000 %h/.config/vosk-wrapper-1000 %h/.cache/vosk-wrapper-1000

# Resource limits
MemoryMax=8G
CPUQuota=100%
```

Adjust these as needed for your system.

## Troubleshooting

### Out of Memory (OOM) Killer

If you see `A process of this unit has been killed by the OOM killer`:

**Causes:**
- Large Vosk models (gigaspeech: 6-10GB RAM)
- MemoryMax limit too restrictive
- Insufficient system RAM
- Memory leak in long-running process

**Solutions:**

1. **Check which model you're using:**
   ```bash
   ls -lh ~/.local/share/vosk-wrapper-1000/models/
   ```

2. **Use a smaller model:**
   ```bash
   # Small model (~50MB, uses ~500MB-1GB RAM)
   vosk-download-model-1000 vosk-model-small-en-us-0.15

   # Medium model (~1GB, uses ~2-3GB RAM)
   vosk-download-model-1000 vosk-model-en-us-0.22

   # Large model (gigaspeech ~2GB, uses 6-10GB RAM)
   vosk-download-model-1000 vosk-model-en-us-0.42-gigaspeech
   ```

3. **Remove or increase memory limit in service file:**
   ```bash
   # Edit service file
   $EDITOR ~/.config/systemd/user/vosk-wrapper-1000-default.service

   # Comment out or increase MemoryMax
   #MemoryMax=12G    # Commented = no limit
   # or
   MemoryMax=16G     # Increase limit

   # Reload and restart
   systemctl --user daemon-reload
   systemctl --user restart vosk-wrapper-1000-default.service
   ```

4. **Check system memory:**
   ```bash
   # Check total RAM
   free -h

   # Check memory usage
   systemctl --user status vosk-wrapper-1000-default.service

   # Monitor memory in real-time
   watch -n 1 'systemctl --user show vosk-wrapper-1000-default.service -p MemoryCurrent'
   ```

5. **Enable swap if you have limited RAM:**
   ```bash
   # Check swap
   swapon --show

   # Create swap file (4GB example)
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile

   # Make permanent (add to /etc/fstab)
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```

6. **Run without systemd to test:**
   ```bash
   # Run manually to see actual memory usage
   vosk-wrapper-1000 daemon --name test --foreground

   # In another terminal, monitor memory
   ps aux | grep vosk-wrapper-1000
   ```

**Memory Requirements by Model:**
- **Small models** (vosk-model-small-*): 500MB - 1GB RAM
- **Medium models** (vosk-model-en-us-0.22): 2GB - 3GB RAM
- **Large models** (gigaspeech): 6GB - 10GB RAM

**Default Configuration:** The service now ships with MemoryMax **disabled** (commented out) to avoid OOM issues. Enable it only if you want to limit resource usage.

### Service Won't Start

1. **Check service status:**
   ```bash
   systemctl --user status vosk-wrapper-1000-default.service
   ```

2. **View detailed logs:**
   ```bash
   journalctl --user -u vosk-wrapper-1000-default.service -n 100
   ```

3. **Test command manually:**
   ```bash
   vosk-wrapper-1000 daemon --name default --foreground
   ```

4. **Check vosk-wrapper-1000 is installed:**
   ```bash
   which vosk-wrapper-1000
   ```

### Service Crashes or Restarts

The service is configured to restart automatically on failure:

```ini
Restart=on-failure
RestartSec=5s
```

Check logs to identify the cause:
```bash
journalctl --user -u vosk-wrapper-1000-default.service -p err
```

### Permission Issues

If you see permission errors:

1. **Ensure directories exist:**
   ```bash
   mkdir -p ~/.local/share/vosk-wrapper-1000/models
   mkdir -p ~/.config/vosk-wrapper-1000
   mkdir -p ~/.cache/vosk-wrapper-1000
   ```

2. **Check directory permissions:**
   ```bash
   ls -la ~/.local/share/vosk-wrapper-1000
   ls -la ~/.config/vosk-wrapper-1000
   ```

### Systemd User Services Not Starting on Boot

Enable lingering to allow user services to run without login:

```bash
# Enable lingering for current user
loginctl enable-linger $USER

# Check if lingering is enabled
loginctl show-user $USER | grep Linger
```

### Service File Not Found

Ensure the service file is in the correct location:

```bash
ls -la ~/.config/systemd/user/vosk-wrapper-1000-default.service
```

Reload systemd after creating/modifying service files:

```bash
systemctl --user daemon-reload
```

## Uninstalling

### Using Setup Script

```bash
# Uninstall default service
./scripts/setup-systemd-service.sh --uninstall

# Uninstall named instance
./scripts/setup-systemd-service.sh --name my-mic --uninstall
```

### Manual Uninstallation

```bash
# Stop and disable service
systemctl --user stop vosk-wrapper-1000-default.service
systemctl --user disable vosk-wrapper-1000-default.service

# Remove service file
rm ~/.config/systemd/user/vosk-wrapper-1000-default.service

# Reload systemd
systemctl --user daemon-reload
```

## Integration Examples

### Start on Login

```bash
# Enable service
systemctl --user enable vosk-wrapper-1000-default.service

# Enable user lingering (service runs even when not logged in)
loginctl enable-linger $USER
```

### Auto-start with Desktop Session

Add to your desktop autostart:

```bash
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/vosk-wrapper-1000.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Vosk Wrapper 1000
Exec=systemctl --user start vosk-wrapper-1000-default.service
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
```

### Keyboard Shortcut to Restart

Add a keyboard shortcut for your desktop environment:

```bash
# Command to bind
systemctl --user restart vosk-wrapper-1000-default.service
```

## Advanced Usage

### Service Dependencies

Make service depend on network or other services:

```ini
[Unit]
After=network-online.target sound.target
Wants=network-online.target
```

### Notifications on Failure

Use systemd to send notifications when service fails:

```bash
# Install notification tool
sudo apt install libnotify-bin  # Debian/Ubuntu
sudo dnf install libnotify      # Fedora

# Create notification script
cat > ~/.local/bin/vosk-failure-notify.sh <<'EOF'
#!/bin/bash
notify-send "Vosk Wrapper Failed" "The vosk-wrapper-1000 service has failed" --urgency=critical
EOF
chmod +x ~/.local/bin/vosk-failure-notify.sh

# Add to service file
[Service]
ExecStopPost=/home/user/.local/bin/vosk-failure-notify.sh
```

### Monitoring with systemd-cgtop

Monitor resource usage:

```bash
# Monitor all user services
systemd-cgtop --user

# Monitor specific service
systemctl --user show vosk-wrapper-1000-default.service -p CPUUsageNSec,MemoryCurrent
```

## See Also

- [Main README](../README.md) - General vosk-wrapper-1000 documentation
- [Configuration Guide](CONFIGURATION.md) - Configuration options
- [IPC Documentation](IPC.md) - Inter-process communication
- [Systemd Documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
