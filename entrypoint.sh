#!/bin/sh
set -e

# Ensures .env exists for local configuration.
if [ ! -f ".env" ]; then
    echo ".env file not found."
    echo "Please create .env file as shown in .env.example."
    exit 0
fi

# Run container
if [ $# -eq 0 ]; then
    echo "No command provided. Keeping container alive."
    tail -f /dev/null
else
    exec "$@"
fi
