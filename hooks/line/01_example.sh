#!/bin/bash

# This is an example LINE hook.
# It is triggered for every line of text transcribed by the model.

# Input:
#   Argument 1: The transcribed text line.
#   Stdin: The full transcript context.
# Output: Standard Output (stdout) and Standard Error (stderr) are logged.

# Return Codes:
# 0   - Continue normal execution.
# 100 - Request to stop listening immediately.
# 101 - Request to terminate the application immediately.

# Read the transcribed text from Argument 1
text="$1"

if [ -n "$text" ]; then
    echo "  [Line Hook] Transcribed: $text" >&2

    # Example: Check for a keyword to stop listening
    if [[ "$text" == *"stop listening"* ]]; then
        echo "  [Line Hook] 'stop listening' command detected." >&2
        exit 100
    fi
fi

exit 0
