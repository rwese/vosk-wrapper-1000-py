#!/bin/bash

# Read all of stdin into a variable
input=$(cat)

# Only copy if there is content
if [ -n "$input" ]; then
    pbcopy <<< "$input"
fi

exit 0
