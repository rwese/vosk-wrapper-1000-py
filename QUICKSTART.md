# Quick Start Guide

## Installation & Setup

### 1. Install vosk-wrapper-1000

```bash
uv tool install git+https://github.com/rwese/vosk-wrapper-1000-py
```

### 2. Setup Systemd Service (Linux)

```bash
cd /path/to/vosk-wrapper-1000-py
./scripts/setup-systemd-service.sh --enable --start
```

### 3. Enable IPC (if needed)

```bash
./scripts/enable-ipc.sh
systemctl --user restart vosk-wrapper-1000-default.service
```

## Basic Usage

### Check Service Status

```bash
systemctl --user status vosk-wrapper-1000-default.service
```

### Control via IPC

```bash
# Toggle listening
vosk-wrapper-1000 send toggle

# Check status
vosk-wrapper-1000 send status

# Stop listening
vosk-wrapper-1000 send stop

# Start listening
vosk-wrapper-1000 send start
```

### Stream Live Transcription

```bash
vosk-wrapper-1000 stream
```

## Troubleshooting

### IPC Not Working

**Symptoms**: `Error: Cannot connect to instance 'default'`

**Solutions**:

1. **Check socket exists**:
   ```bash
   ls -la /run/user/$(id -u)/vosk-wrapper-1000/
   ```

2. **Enable IPC in config**:
   ```bash
   ./scripts/enable-ipc.sh
   ```

3. **Check service logs**:
   ```bash
   journalctl --user -u vosk-wrapper-1000-default.service | grep IPC
   ```

   Should see: `IPC server listening on /run/user/1000/vosk-wrapper-1000/default.sock`

4. **Verify config**:
   ```bash
   cat ~/.config/vosk-wrapper-1000/config.yaml | grep -A4 "^ipc:"
   ```

   Should have:
   ```yaml
   ipc:
     enabled: true
     socket_path: "/run/user/1000/vosk-wrapper-1000/{instance_name}.sock"
   ```

### OOM (Out of Memory) Issues

**Symptoms**: Service gets killed, logs show `OOM killer`

**Solutions**:

1. **Run OOM fix script**:
   ```bash
   ./scripts/fix-oom-issue.sh
   ```

2. **Use smaller model**:
   ```bash
   vosk-download-model-1000 vosk-model-small-en-us-0.15
   ```

3. **Check memory usage**:
   ```bash
   systemctl --user status vosk-wrapper-1000-default.service
   ```

### Service Won't Start

1. **Check logs**:
   ```bash
   journalctl --user -u vosk-wrapper-1000-default.service -n 50
   ```

2. **Test manually**:
   ```bash
   vosk-wrapper-1000 daemon --name test --foreground
   ```

3. **Verify model exists**:
   ```bash
   ls -la ~/.local/share/vosk-wrapper-1000/models/
   ```

## Common Tasks

### Download a Model

```bash
vosk-download-model-1000 vosk-model-small-en-us-0.15
```

### Change Log Level

Edit `~/.config/vosk-wrapper-1000/config.yaml`:

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
```

Then restart:

```bash
systemctl --user restart vosk-wrapper-1000-default.service
```

### View Logs

```bash
# Follow logs in real-time
journalctl --user -u vosk-wrapper-1000-default.service -f

# Last 50 lines
journalctl --user -u vosk-wrapper-1000-default.service -n 50

# Errors only
journalctl --user -u vosk-wrapper-1000-default.service -p err
```

## Documentation

- [Full README](README.md)
- [Systemd Service Guide](docs/SYSTEMD_SERVICE.md)
- [IPC Documentation](docs/IPC_PROTOCOL.md)
- [Configuration Guide](docs/CONFIGURATION.md)
