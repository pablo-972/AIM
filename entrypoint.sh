#!/bin/bash
set -e


# Ensures .env exists and loads it
if [ ! -f ".env" ]; then
    echo ".env file not found."
    echo "Please create .env file as show as example."
    exit 0
else
    source .env
fi


# # Start Ollama in background
# ollama serve &


# # Wait until Ollama is ready
# echo "Waiting for Ollama to start..."
# until curl http://localhost:11434/api/tags > /dev/null; do
#     sleep 2
# done
# echo "Ollama is ready."


# # Pull local models requested by the deployment.
# if [ ! -z "$OLLAMA_PRELOAD_MODELS" ]; then
#     for model in $OLLAMA_PRELOAD_MODELS; do
#         echo "Pulling Ollama model: $model"
#         ollama pull "$model"
#     done
# fi


# Run container
if [ $# -eq 0 ]; then
    echo "No command provided. Keeping container alive."
    tail -f /dev/null
else
    exec "$@"
fi
