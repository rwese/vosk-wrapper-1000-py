#!/bin/bash
# Cross-platform clipboard hook
# Copies transcript text to system clipboard
# Supports: macOS (pbcopy), Linux (xclip/xsel), Wayland (wl-copy)
# Handles timeouts and empty input gracefully

# Detect clipboard tool
if [[ "$OSTYPE" == "darwin"* ]]; then
    clipboard_cmd="pbcopy"
elif command -v xclip >/dev/null 2>&1; then
    clipboard_cmd="xclip -selection clipboard"
elif command -v xsel >/dev/null 2>&1; then
    clipboard_cmd="xsel --clipboard"
elif command -v wl-copy >/dev/null 2>&1; then
    clipboard_cmd="wl-copy --trim-newline"
else
    echo "Error: No clipboard tool found. Install xclip, xsel, or wl-clipboard." >&2
    exit 1
fi

# Read input with timeout protection
if [ -t 0 ]; then
    echo "Warning: No input provided to clipboard hook" >&2
    exit 0
fi

# Try to read with timeout (5 seconds)
if command -v timeout >/dev/null 2>&1; then
    input=$(timeout 5 cat 2>/dev/null)
    timeout_exit=$?
    if [ $timeout_exit -eq 124 ]; then
        echo "Warning: Timeout reading input for clipboard hook" >&2
        exit 0
    elif [ $timeout_exit -ne 0 ]; then
        echo "Error: Failed to read input (exit code: $timeout_exit)" >&2
        exit 1
    fi
else
    # Fallback without timeout (less safe)
    input=$(cat 2>/dev/null)
fi



# Copy if we have content
if [ -n "$input" ]; then
    # Strip trailing whitespace for clean clipboard content
    clean_input=$(printf '%s' "$input" | sed 's/[[:space:]]*$//')

    if printf '%s' "$clean_input" | $clipboard_cmd 2>/dev/null; then
        char_count=$(printf '%s' "$clean_input" | wc -c | tr -d ' ')
        echo "Copied transcript to clipboard ($char_count chars)" >&2
    else
        echo "Error: Failed to copy to clipboard" >&2
        exit 1
    fi
else
    echo "Warning: No content to copy to clipboard" >&2
fi

exit 0
