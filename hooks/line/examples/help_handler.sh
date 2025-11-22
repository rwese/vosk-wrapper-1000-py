#!/bin/bash
# Example script called when "help" trigger word is detected
# Arguments:
#   $1 - Current line text containing the trigger
# Stdin: Full transcript context

CURRENT_LINE="$1"

echo "Help trigger detected!" >&2
echo "Current line: $CURRENT_LINE" >&2

# Example actions:
# - Display available commands
# - Log help request
# - Send notification
# - Update statistics

# Read full context if needed
if [ -t 0 ]; then
    echo "No context provided via stdin" >&2
else
    CONTEXT=$(cat)
    echo "Full context length: ${#CONTEXT} chars" >&2
fi

# Example: Log to a file
LOG_FILE="/tmp/vosk_help_requests.log"
echo "$(date): Help requested - $CURRENT_LINE" >> "$LOG_FILE"

# Example: Could call another service
# curl -X POST https://example.com/api/help -d "{\"text\":\"$CURRENT_LINE\"}"

exit 0
