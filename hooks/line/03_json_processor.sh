#!/bin/bash

# Example JSON hook for LINE events
# This hook receives structured JSON data for each transcribed line
# Filename contains 'json' so it gets JSON payload instead of plain text

# Read the JSON payload from stdin
json_payload=$(cat)

# Parse the JSON data
echo "📝 New transcript line received:" >&2
echo "$json_payload" >&2

# Extract the transcript data
transcript=$(echo "$json_payload" | sed 's/.*"data":"\([^"]*\)".*/\1/')
timestamp=$(echo "$json_payload" | sed 's/.*"timestamp":\([0-9.]*\).*/\1/')

echo "Transcript: '$transcript'" >&2
echo "Timestamp: $timestamp" >&2

# Example: Word count analysis
word_count=$(echo "$transcript" | wc -w)
echo "Word count: $word_count" >&2

# Example: Check for specific keywords
if echo "$transcript" | grep -qi "stop\|quit\|exit"; then
    echo "🛑 Detected stop command in transcript" >&2
    # Could return exit code 100 to stop listening
    # exit 100
fi

# Example: Send to external service for processing
# curl -X POST -H "Content-Type: application/json" \
#      -d "$json_payload" \
#      http://your-transcript-service.com/process

# Example: Append to a JSON log file
# echo "$json_payload" >> /tmp/transcript_log.json

exit 0
