#!/bin/bash

# This is an example START hook.
# It is triggered when the application starts listening (SIGUSR1).

# Input: None
# Output: Standard Output (stdout) and Standard Error (stderr) are logged.

# Return Codes:
# 0   - Continue normal execution.
# 100 - Request to stop listening immediately.
# 101 - Request to terminate the application immediately.

echo "  [Start Hook] Listening started..." >&2
exit 0
