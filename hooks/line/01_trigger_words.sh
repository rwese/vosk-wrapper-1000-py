#!/bin/bash

# Trigger Word Hook
# Argument 1: Current line text
# Stdin: Full transcript context

CURRENT_LINE="$1"

# Check for "breaker" - Stop Listening (100)
if [[ "$CURRENT_LINE" == *"breaker"* ]]; then
    echo "Trigger word 'breaker' detected." >&2
    exit 100
fi

# Check for "shutdown" - Terminate (101)
if [[ "$CURRENT_LINE" == *"shutdown"* ]]; then
    echo "Trigger word 'shutdown' detected." >&2
    exit 101
fi

# Check for "abort" - Abort (102)
if [[ "$CURRENT_LINE" == *"abort"* ]]; then
    echo "Trigger word 'abort' detected." >&2
    exit 102
fi

exit 0
