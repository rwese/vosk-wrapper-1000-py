#!/bin/bash
# Types the input text into the active window.
# Useful for dictation or pasting the transcript.

# Read stdin
input=$(cat)

if [ -z "$input" ]; then
    exit 0
fi

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS Implementation
    # Requires "Accessibility" permissions for the terminal/application.

    # Escape special characters for AppleScript
    # 1. Escape backslashes
    # 2. Escape double quotes
    escaped_input=$(echo "$input" | sed 's/\\/\\\\/g; s/"/\\"/g')

    osascript -e "tell application \"System Events\" to keystroke \"$escaped_input\""

elif command -v xdotool >/dev/null 2>&1; then
    # Linux Implementation (requires xdotool)
    xdotool type --clearmodifiers --delay 0 "$input"

elif command -v wtype >/dev/null 2>&1; then
    # Wayland Implementation (requires wtype)
    wtype "$input"

else
    echo "Error: No typing tool found. Install 'xdotool' (X11) or 'wtype' (Wayland) on Linux." >&2
    exit 1
fi
