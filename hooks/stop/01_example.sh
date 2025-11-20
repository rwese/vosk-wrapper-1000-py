#!/bin/bash

# This is an example STOP hook.
# It is triggered when the application stops listening (SIGUSR2).

# Input: None
# Output: Standard Output (stdout) and Standard Error (stderr) are logged.

# Return Codes:
# 0   - Continue normal execution.
# 101 - Request to terminate the application immediately.

echo "  [Stop Hook] Listening stopped." >&2
exit 0
