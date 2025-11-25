#!/usr/bin/env bash
# Setup systemd user service for vosk-wrapper-1000

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SYSTEMD_USER_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}ℹ${NC} $*"
}

print_success() {
    echo -e "${GREEN}✓${NC} $*"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $*"
}

print_error() {
    echo -e "${RED}✗${NC} $*"
}

show_usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Setup systemd user service for vosk-wrapper-1000

OPTIONS:
    -n, --name NAME         Instance name (default: default)
    -e, --enable            Enable service to start on boot
    -s, --start             Start service immediately
    -u, --uninstall         Uninstall the service
    -h, --help              Show this help message

EXAMPLES:
    # Install default service
    $(basename "$0")

    # Install and enable service
    $(basename "$0") --enable

    # Install, enable, and start service
    $(basename "$0") --enable --start

    # Install named instance
    $(basename "$0") --name my-mic --enable --start

    # Uninstall service
    $(basename "$0") --uninstall

SYSTEMD COMMANDS:
    # View logs
    journalctl --user -u vosk-wrapper-1000-default.service -f

    # Check status
    systemctl --user status vosk-wrapper-1000-default.service

    # Start/stop/restart
    systemctl --user start vosk-wrapper-1000-default.service
    systemctl --user stop vosk-wrapper-1000-default.service
    systemctl --user restart vosk-wrapper-1000-default.service

    # Enable/disable
    systemctl --user enable vosk-wrapper-1000-default.service
    systemctl --user disable vosk-wrapper-1000-default.service
EOF
}

# Parse arguments
INSTANCE_NAME="default"
ENABLE_SERVICE=false
START_SERVICE=false
UNINSTALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            INSTANCE_NAME="$2"
            shift 2
            ;;
        -e|--enable)
            ENABLE_SERVICE=true
            shift
            ;;
        -s|--start)
            START_SERVICE=true
            shift
            ;;
        -u|--uninstall)
            UNINSTALL=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

SERVICE_NAME="vosk-wrapper-1000-${INSTANCE_NAME}.service"
SERVICE_FILE="${SYSTEMD_USER_DIR}/${SERVICE_NAME}"

# Check if vosk-wrapper-1000 is installed
if ! command -v vosk-wrapper-1000 &> /dev/null; then
    print_error "vosk-wrapper-1000 is not installed or not in PATH"
    print_info "Install it with: uv tool install git+https://github.com/rwese/vosk-wrapper-1000-py"
    exit 1
fi

VOSK_BIN="$(command -v vosk-wrapper-1000)"
print_info "Found vosk-wrapper-1000 at: $VOSK_BIN"

# Uninstall mode
if [[ "$UNINSTALL" == true ]]; then
    print_info "Uninstalling systemd service: $SERVICE_NAME"

    if systemctl --user is-active --quiet "$SERVICE_NAME"; then
        print_info "Stopping service..."
        systemctl --user stop "$SERVICE_NAME"
        print_success "Service stopped"
    fi

    if systemctl --user is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        print_info "Disabling service..."
        systemctl --user disable "$SERVICE_NAME"
        print_success "Service disabled"
    fi

    if [[ -f "$SERVICE_FILE" ]]; then
        rm "$SERVICE_FILE"
        print_success "Service file removed: $SERVICE_FILE"
        systemctl --user daemon-reload
        print_success "Systemd daemon reloaded"
    else
        print_warning "Service file not found: $SERVICE_FILE"
    fi

    exit 0
fi

# Create systemd user directory if it doesn't exist
if [[ ! -d "$SYSTEMD_USER_DIR" ]]; then
    print_info "Creating systemd user directory: $SYSTEMD_USER_DIR"
    mkdir -p "$SYSTEMD_USER_DIR"
fi

# Generate service file
print_info "Generating service file: $SERVICE_FILE"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Vosk Wrapper 1000 Speech Recognition Daemon ($INSTANCE_NAME)
Documentation=https://github.com/rwese/vosk-wrapper-1000-py
After=sound.target

[Service]
Type=simple
ExecStart=$VOSK_BIN daemon --name $INSTANCE_NAME --foreground
Restart=on-failure
RestartSec=5s

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=%h/.local/share/vosk-wrapper-1000 %h/.config/vosk-wrapper-1000 %h/.cache/vosk-wrapper-1000

# Runtime directory for IPC socket (creates /run/user/UID/vosk-wrapper-1000/)
RuntimeDirectory=vosk-wrapper-1000
RuntimeDirectoryMode=0755

# Resource limits
# Note: Large models (gigaspeech) can use 6-10GB RAM
# Small models typically use 1-2GB RAM
# Adjust MemoryMax based on your model and system RAM
# Comment out MemoryMax to disable the limit if you have OOM issues
#MemoryMax=12G
CPUQuota=150%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vosk-wrapper-1000-$INSTANCE_NAME

[Install]
WantedBy=default.target
EOF

print_success "Service file created"

# Reload systemd daemon
print_info "Reloading systemd daemon..."
systemctl --user daemon-reload
print_success "Systemd daemon reloaded"

# Enable service if requested
if [[ "$ENABLE_SERVICE" == true ]]; then
    print_info "Enabling service to start on boot..."
    systemctl --user enable "$SERVICE_NAME"
    print_success "Service enabled"
fi

# Start service if requested
if [[ "$START_SERVICE" == true ]]; then
    print_info "Starting service..."
    systemctl --user start "$SERVICE_NAME"
    print_success "Service started"

    sleep 2

    if systemctl --user is-active --quiet "$SERVICE_NAME"; then
        print_success "Service is running"
        systemctl --user status "$SERVICE_NAME" --no-pager
    else
        print_error "Service failed to start"
        print_info "Check logs with: journalctl --user -u $SERVICE_NAME -n 50"
        exit 1
    fi
fi

print_success "Setup complete!"
echo ""
print_info "Useful commands:"
echo "  Start:   systemctl --user start $SERVICE_NAME"
echo "  Stop:    systemctl --user stop $SERVICE_NAME"
echo "  Status:  systemctl --user status $SERVICE_NAME"
echo "  Logs:    journalctl --user -u $SERVICE_NAME -f"
echo "  Enable:  systemctl --user enable $SERVICE_NAME"
echo "  Disable: systemctl --user disable $SERVICE_NAME"
