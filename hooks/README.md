# Hook Scripts

This directory contains hook scripts that are executed by the Vosk Wrapper service at specific events.

## Directory Structure

- `start/`: Scripts executed when listening starts (SIGUSR1).
- `stop/`: Scripts executed when listening stops (SIGUSR2).
- `line/`: Scripts executed after each recognized line of text.

## Writing Hooks

Hooks can be written in any language (Bash, Python, Ruby, etc.), provided they are executable.

### Requirements

1. **Executable**: The file must have executable permissions (`chmod +x script.sh`).
2. **Shebang**: Ideally, include a shebang line (e.g., `#!/bin/bash` or `#!/usr/bin/env python3`) at the top.
   - *Note*: If a shebang is missing, the service will attempt to run the script using `/bin/sh`.

### Input (stdin)

The service passes relevant data to the hook's standard input (`stdin`):

- **stop**: Receives the full transcript of the session.
- **line**: Receives the full transcript so far.

### Arguments

- **line**: The script receives the last recognized line as the first argument (`$1` in Bash, `sys.argv[1]` in Python).

### Return Codes

Hooks can control the service by returning specific exit codes:

- `0`: Continue normal operation.
- `100`: Stop listening (equivalent to sending SIGUSR2).
- `101`: Terminate the application (equivalent to sending SIGTERM).
- `102`: Abort immediately.

## Examples

### Bash (Simple)
```bash
#!/bin/bash
# Read stdin
input=$(cat)
echo "Received: $input" >> /tmp/log.txt
```

### Python
```python
#!/usr/bin/env python3
import sys

# Read stdin
data = sys.stdin.read()
print(f"Received {len(data)} bytes", file=sys.stderr)
```

### Pbcopy (macOS Clipboard)
```bash
#!/bin/bash
input=$(cat)
if [ -n "$input" ]; then
    pbcopy <<< "$input"
fi
```
