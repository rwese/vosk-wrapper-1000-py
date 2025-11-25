#!/usr/bin/env bash
# Quick fix for OOM (Out Of Memory) issues with vosk-wrapper-1000 systemd service

set -euo pipefail

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

SYSTEMD_USER_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
INSTANCE_NAME="${1:-default}"
SERVICE_NAME="vosk-wrapper-1000-${INSTANCE_NAME}.service"
SERVICE_FILE="${SYSTEMD_USER_DIR}/${SERVICE_NAME}"

echo "=== Vosk Wrapper 1000 OOM Issue Fix ==="
echo ""

# Check if service exists
if [[ ! -f "$SERVICE_FILE" ]]; then
    print_error "Service file not found: $SERVICE_FILE"
    print_info "Run setup-systemd-service.sh first to create the service"
    exit 1
fi

print_info "Found service: $SERVICE_NAME"

# Check system memory
TOTAL_RAM=$(free -h | awk '/^Mem:/ {print $2}')
AVAILABLE_RAM=$(free -h | awk '/^Mem:/ {print $7}')
print_info "System RAM: $TOTAL_RAM total, $AVAILABLE_RAM available"

# Check current models
print_info "Checking installed models..."
MODELS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/vosk-wrapper-1000/models"
if [[ -d "$MODELS_DIR" ]]; then
    echo ""
    echo "Installed models:"
    ls -lh "$MODELS_DIR" | awk 'NR>1 {printf "  - %-40s %8s\n", $9, $5}'
    echo ""
fi

# Check for gigaspeech model
if ls "$MODELS_DIR"/*gigaspeech* &>/dev/null 2>&1; then
    print_warning "Large gigaspeech model detected (uses 6-10GB RAM)"
    print_info "Consider using a smaller model for systems with limited RAM"
fi

# Check current MemoryMax setting
CURRENT_MEMORY_MAX=$(grep -E "^MemoryMax=" "$SERVICE_FILE" || echo "none")
if [[ "$CURRENT_MEMORY_MAX" != "none" ]]; then
    print_warning "Current memory limit: $CURRENT_MEMORY_MAX"
else
    print_info "Current memory limit: none (unlimited)"
fi

echo ""
print_info "Fix options:"
echo "  1) Remove memory limit (recommended)"
echo "  2) Increase memory limit to 16GB"
echo "  3) Switch to a smaller model"
echo "  4) Check memory usage and exit"
echo "  5) Exit without changes"
echo ""

read -p "Choose option (1-5): " choice

case $choice in
    1)
        print_info "Removing memory limit from service file..."
        sed -i.bak 's/^MemoryMax=/#MemoryMax=/' "$SERVICE_FILE"
        print_success "Memory limit removed (backed up to ${SERVICE_FILE}.bak)"

        print_info "Reloading systemd..."
        systemctl --user daemon-reload

        print_info "Restarting service..."
        systemctl --user restart "$SERVICE_NAME"

        sleep 2
        if systemctl --user is-active --quiet "$SERVICE_NAME"; then
            print_success "Service restarted successfully!"
            systemctl --user status "$SERVICE_NAME" --no-pager
        else
            print_error "Service failed to start"
            print_info "Check logs: journalctl --user -u $SERVICE_NAME -n 50"
        fi
        ;;

    2)
        print_info "Setting memory limit to 16GB..."
        sed -i.bak 's/^#\?MemoryMax=.*/MemoryMax=16G/' "$SERVICE_FILE"
        print_success "Memory limit set to 16GB (backed up to ${SERVICE_FILE}.bak)"

        print_info "Reloading systemd..."
        systemctl --user daemon-reload

        print_info "Restarting service..."
        systemctl --user restart "$SERVICE_NAME"

        sleep 2
        if systemctl --user is-active --quiet "$SERVICE_NAME"; then
            print_success "Service restarted successfully!"
            systemctl --user status "$SERVICE_NAME" --no-pager
        else
            print_error "Service failed to start"
            print_info "Check logs: journalctl --user -u $SERVICE_NAME -n 50"
        fi
        ;;

    3)
        print_info "Available small models:"
        echo "  - vosk-model-small-en-us-0.15 (~50MB, uses ~500MB-1GB RAM)"
        echo "  - vosk-model-en-us-0.22 (~1GB, uses ~2-3GB RAM)"
        echo ""
        print_info "Download a small model:"
        echo "  vosk-download-model-1000 vosk-model-small-en-us-0.15"
        echo ""
        print_info "Then update your config to use it:"
        echo "  vosk-settings-tui"
        echo "  or edit ~/.config/vosk-wrapper-1000/config.yaml"
        ;;

    4)
        print_info "Checking memory usage..."
        echo ""

        if systemctl --user is-active --quiet "$SERVICE_NAME"; then
            print_info "Service status:"
            systemctl --user status "$SERVICE_NAME" --no-pager
            echo ""

            print_info "Memory usage:"
            systemctl --user show "$SERVICE_NAME" -p MemoryCurrent | \
                awk -F= '{printf "  Current: %.2f GB\n", $2/1024/1024/1024}'

            echo ""
            print_info "To monitor in real-time:"
            echo "  watch -n 1 'systemctl --user show $SERVICE_NAME -p MemoryCurrent'"
        else
            print_warning "Service is not running"
        fi

        echo ""
        print_info "System memory:"
        free -h
        ;;

    5)
        print_info "Exiting without changes"
        exit 0
        ;;

    *)
        print_error "Invalid option"
        exit 1
        ;;
esac

echo ""
print_info "Additional tips:"
echo "  - View logs: journalctl --user -u $SERVICE_NAME -f"
echo "  - Check status: systemctl --user status $SERVICE_NAME"
echo "  - Restart: systemctl --user restart $SERVICE_NAME"
