#!/usr/bin/env bash
# Enable IPC for vosk-wrapper-1000

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ${NC} $*"
}

print_success() {
    echo -e "${GREEN}✓${NC} $*"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $*"
}

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/vosk-wrapper-1000"
CONFIG_FILE="$CONFIG_DIR/config.yaml"

echo "=== Enable IPC for vosk-wrapper-1000 ==="
echo ""

# Create config directory if needed
if [[ ! -d "$CONFIG_DIR" ]]; then
    print_info "Creating config directory: $CONFIG_DIR"
    mkdir -p "$CONFIG_DIR"
fi

# Create or update config file
if [[ -f "$CONFIG_FILE" ]]; then
    print_info "Config file exists: $CONFIG_FILE"

    # Check if IPC section exists
    if grep -q "^ipc:" "$CONFIG_FILE"; then
        # Update existing IPC section
        print_info "Updating IPC configuration..."
        sed -i.bak 's/^  enabled: false$/  enabled: true/' "$CONFIG_FILE"
        print_success "IPC enabled in existing config (backup: ${CONFIG_FILE}.bak)"
    else
        # Add IPC section
        print_info "Adding IPC section to config..."
        cat >> "$CONFIG_FILE" <<'EOF'

# IPC Settings
ipc:
  enabled: true
  socket_path: "/run/user/1000/vosk-wrapper-1000/{instance_name}.sock"
  send_partials: true
  timeout: 5.0
EOF
        print_success "IPC section added to config"
    fi
else
    # Create new config file
    print_info "Creating new config file with IPC enabled..."
    cat > "$CONFIG_FILE" <<'EOF'
# Vosk Wrapper 1000 Configuration

# IPC Settings
ipc:
  enabled: true
  socket_path: "/tmp/vosk-wrapper-{instance_name}.sock"
  send_partials: true
  timeout: 5.0

# Logging
logging:
  level: "INFO"
EOF
    print_success "Config file created: $CONFIG_FILE"
fi

echo ""
print_info "Verifying IPC configuration..."
echo ""
grep -A4 "^ipc:" "$CONFIG_FILE" || echo "IPC section not found in config"

echo ""
print_success "IPC enabled!"
echo ""
print_info "Next steps:"
echo "  1. Restart the service: systemctl --user restart vosk-wrapper-1000-default.service"
echo "  2. Check IPC socket: ls -la /tmp/vosk-wrapper-*.sock"
echo "  3. Test IPC: vosk-wrapper-1000 send status"
echo "  4. View logs: journalctl --user -u vosk-wrapper-1000-default.service -f"
