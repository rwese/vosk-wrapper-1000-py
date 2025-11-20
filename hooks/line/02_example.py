#!/usr/bin/env python3
import sys

# This is an example Python LINE hook.
# It is triggered for every line of text transcribed by the model.

# Input: The transcribed text line is passed via Standard Input (stdin).
# Output: Standard Output (stdout) and Standard Error (stderr) are logged.

# Return Codes:
# 0   - Continue normal execution.
# 100 - Request to stop listening immediately.
# 101 - Request to terminate the application immediately.

def main():
    # Read the transcribed text from stdin
    try:
        text = sys.stdin.read().strip()
    except Exception:
        text = ""

    if text:
        print(f"  [Python Line Hook] Transcribed: {text}", file=sys.stderr)

        # Example: Check for a keyword to stop listening
        if "stop listening" in text.lower():
            print("  [Python Line Hook] 'stop listening' command detected.", file=sys.stderr)
            sys.exit(100)

if __name__ == "__main__":
    main()
