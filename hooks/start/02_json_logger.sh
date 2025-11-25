#!/bin/bash

# Example JSON hook for START events
# This hook receives structured JSON data when listening starts
# Filename contains 'json' so it gets JSON payload instead of plain text

# Read the JSON payload from stdin
json_payload=$(cat)

# Parse the JSON data (basic parsing for demonstration)
echo "🎤 Listening started - received JSON event:" >&2
echo "$json_payload" >&2

# Extract event type for validation
event_type=$(echo "$json_payload" | sed 's/.*"event":"\([^"]*\)".*/\1/')
if [ "$event_type" = "start" ]; then
    echo "✅ Valid start event received" >&2
else
    echo "❌ Unexpected event type: $event_type" >&2
fi

# Example: Log the start time
timestamp=$(echo "$json_payload" | sed 's/.*"timestamp":\([0-9.]*\).*/\1/')
echo "Started at: $(date -d "@$timestamp" 2>/dev/null || echo "timestamp: $timestamp")" >&2

# Example: Send notification or trigger external service
# curl -X POST -H "Content-Type: application/json" \
#      -d "$json_payload" \
#      http://your-service.com/listening-started

exit 0
