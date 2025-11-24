#!/bin/bash

# Example JSON hook for vosk-wrapper-1000
# This hook receives transcript data in JSON format
# Filename contains 'json' so it gets JSON payload instead of plain text

# Read the JSON payload from stdin
json_payload=$(cat)

# Parse and process the JSON (using jq if available, or basic shell parsing)
echo "Received JSON transcript data:" >&2
echo "$json_payload" >&2

# Example: Extract just the transcript text
# Using basic shell JSON parsing (for demonstration)
# In production, you might want to use jq or a proper JSON parser

# Simple extraction (this is basic - real implementation would use jq)
data=$(echo "$json_payload" | sed 's/.*"data":"\([^"]*\)".*/\1/')

if [ -n "$data" ]; then
    echo "Transcript: $data" >&2
    # Do something with the transcript data
    # For example, send to another service, log to database, etc.
fi

exit 0