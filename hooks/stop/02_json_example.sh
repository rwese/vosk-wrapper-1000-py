#!/bin/bash

# Example JSON hook for STOP events
# This hook receives structured JSON data when listening stops
# Filename contains 'json' so it gets JSON payload instead of plain text

# Read the JSON payload from stdin
json_payload=$(cat)

# Parse the JSON data
echo "🛑 Listening stopped - final transcript received:" >&2
echo "$json_payload" >&2

# Extract the transcript data
transcript=$(echo "$json_payload" | sed 's/.*"data":"\([^"]*\)".*/\1/')
timestamp=$(echo "$json_payload" | sed 's/.*"timestamp":\([0-9.]*\).*/\1/')

echo "Final transcript: '$transcript'" >&2
echo "Stopped at: $timestamp" >&2

# Example: Calculate session statistics
if [ -n "$transcript" ]; then
    char_count=$(echo -n "$transcript" | wc -c)
    word_count=$(echo "$transcript" | wc -w)
    line_count=$(echo "$transcript" | wc -l)

    echo "Session stats:" >&2
    echo "  Characters: $char_count" >&2
    echo "  Words: $word_count" >&2
    echo "  Lines: $line_count" >&2
else
    echo "No transcript data collected in this session" >&2
fi

# Example: Save to file with timestamp
# output_file="/tmp/transcript_$(date +%Y%m%d_%H%M%S).json"
# echo "$json_payload" > "$output_file"
# echo "Saved transcript to: $output_file" >&2

# Example: Send final transcript to external service
# curl -X POST -H "Content-Type: application/json" \
#      -d "$json_payload" \
#      http://your-service.com/session-complete

exit 0