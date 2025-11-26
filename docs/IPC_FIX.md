# IPC Socket Path Fix for Systemd Services

## Summary

The IPC (Inter-Process Communication) system wasn't accessible when running
vosk-wrapper-1000 as a systemd service due to the `PrivateTmp=true` security
setting.

## The Problem

1. **Systemd Security**: The service used `PrivateTmp=true` which creates a
private `/tmp` directory
2. **Socket Isolation**: IPC sockets created in the service's private `/tmp`
weren't accessible from outside
3. **Hidden Logging**: Default log level was `ERROR`, hiding INFO messages
about IPC startup
4. **Default Path**: IPC client defaulted to
`/tmp/vosk-wrapper-{instance_name}.sock`

## The Solution

### 1. Changed Default Socket Location

**From:** `/tmp/vosk-wrapper-{instance_name}.sock`
**To:** `/run/user/1000/vosk-wrapper-{instance_name}.sock`

Why:
- `/run/user/UID` is the standard XDG runtime directory
- Compatible with systemd sandboxing
- Accessible from both inside and outside the service
- Automatically cleaned up on logout

### 2. Updated Systemd Service

Added `/run/user/%U` to `ReadWritePaths`:

```ini
ReadWritePaths=%h/.local/share/vosk-wrapper-1000 %h/.config/vosk-wrapper-1000
%h/.cache/vosk-wrapper-1000 /run/user/%U
```

### 3. Smart Socket Path Resolution

Updated `get_socket_path()` in `ipc_client.py` to:
1. Read from config file first
2. Fall back to `/run/user/UID` if available
3. Fall back to `/tmp` for non-systemd environments

### 4. Default Configuration

Updated `config/default.yaml` to use `/run/user/1000` by default.

## For Users

### After Updating

1. **Reinstall** (to get code changes):
   ```bash
   uv tool install --force git+https://github.com/rwese/vosk-wrapper-1000-py
   ```

2. **Update Config** (or create new one):
   ```bash
   # Edit config
   $EDITOR ~/.config/vosk-wrapper-1000/config.yaml

   # Change socket_path to:
   ipc:
     enabled: true
     socket_path: "/run/user/1000/vosk-wrapper-{instance_name}.sock"
   ```

3. **Reinstall Service**:
   ```bash
   # Uninstall old service
   ./scripts/setup-systemd-service.sh --uninstall

   # Install new service
   ./scripts/setup-systemd-service.sh --enable --start
   ```

4. **Verify** IPC works:
   ```bash
   # Check socket exists
   ls -la /run/user/1000/vosk-wrapper-*.sock

   # Test IPC commands
   vosk-wrapper-1000 send status
   vosk-wrapper-1000 send toggle
   ```

### Quick Fix Script

For existing installations:

```bash
# 1. Enable IPC in config
./scripts/enable-ipc.sh

# 2. Update socket path
sed -i 's|/tmp/vosk-wrapper-|/run/user/1000/vosk-wrapper-|' \
~/.config/vosk-wrapper-1000/config.yaml

# 3. Reinstall service
./scripts/setup-systemd-service.sh --uninstall
./scripts/setup-systemd-service.sh --enable --start

# 4. Test
vosk-wrapper-1000 send status
```

## Technical Details

### Socket Path Priority

The system resolves socket paths in this order:

1. **Config file** (`~/.config/vosk-wrapper-1000/config.yaml`):
   ```yaml
   ipc:
     socket_path: "/run/user/1000/vosk-wrapper-{instance_name}.sock"
   ```

2. **Runtime directory** (if writable):
`/run/user/$(id -u)/vosk-wrapper-{instance_name}.sock`

3. **Fallback**: `/tmp/vosk-wrapper-{instance_name}.sock` (for non-systemd
systems)

### Systemd Integration

The service file now includes:

```ini
[Service]
# Security hardening
PrivateTmp=true  # Still enabled for security
ProtectSystem=strict
ProtectHome=read-only

# Allow access to runtime directory
ReadWritePaths=%h/.local/share/vosk-wrapper-1000 %h/.config/vosk-wrapper-1000
%h/.cache/vosk-wrapper-1000 /run/user/%U
```

### Log Level Configuration

To see IPC startup messages, ensure logging level is INFO or DEBUG:

```yaml
logging:
  level: "INFO"  # Was "ERROR" by default
```

## Testing

### Verify Socket Creation

```bash
# Start service
systemctl --user restart vosk-wrapper-1000-default.service

# Wait for model loading
sleep 30

# Check socket exists
ls -la /run/user/$(id -u)/vosk-wrapper-*.sock

# Should show:
# srwxr-xr-x. 1 user user 0 Nov 25 17:15
# /run/user/1000/vosk-wrapper-default.sock
```

### Test IPC Commands

```bash
# Status
vosk-wrapper-1000 send status

# Toggle listening
vosk-wrapper-1000 send toggle

# Get transcript
vosk-wrapper-1000 send transcript

# List devices
vosk-wrapper-1000 send devices

# Stream transcription
vosk-wrapper-1000 stream
```

## Troubleshooting

### Socket Not Found

```bash
# Check if service is running
systemctl --user status vosk-wrapper-1000-default.service

# Check logs for IPC startup
journalctl --user -u vosk-wrapper-1000-default.service | grep IPC

# Should see:
# IPC server listening on /run/user/1000/vosk-wrapper-default.sock
```

### Permission Denied

```bash
# Ensure runtime directory is writable
ls -ld /run/user/$(id -u)

# Should show:
# drwx------ user user /run/user/1000
```

### Still Using /tmp

```bash
# Check config socket_path
grep socket_path ~/.config/vosk-wrapper-1000/config.yaml

# Update if needed
sed -i 's|/tmp/vosk-wrapper-|/run/user/1000/vosk-wrapper-|' \
~/.config/vosk-wrapper-1000/config.yaml

# Restart service
systemctl --user restart vosk-wrapper-1000-default.service
```

## See Also

- [IPC Documentation](IPC.md) - Complete IPC protocol and usage
- [Systemd Service Setup](SYSTEMD_SERVICE.md) - Service configuration guide
- [Configuration Guide](CONFIGURATION.md) - Configuration options
