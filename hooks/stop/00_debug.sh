#!/bin/bash
# Debug hook to test stdin
echo "=== STOP HOOK DEBUG ===" >> /tmp/stop_hook_debug.log
echo "Timestamp: $(date)" >> /tmp/stop_hook_debug.log
echo "Stdin is a terminal: $([ -t 0 ] && echo 'YES (no input)' || echo 'NO (has input)')" >> /tmp/stop_hook_debug.log
echo "Input received:" >> /tmp/stop_hook_debug.log
cat >> /tmp/stop_hook_debug.log
echo "" >> /tmp/stop_hook_debug.log
echo "=== END ===" >> /tmp/stop_hook_debug.log
exit 0
