#!/bin/bash
set -e

ollama serve &
ollama_pid="$!"

echo "Waiting for Ollama to start..."
until curl -fsS "http://localhost:11434/api/tags" > /dev/null; do
    sleep 2
done
echo "Ollama is ready."

if [ -n "${OLLAMA_PRELOAD_MODELS:-}" ]; then
    for model in $OLLAMA_PRELOAD_MODELS; do
        echo "Pulling Ollama model: $model"
        ollama pull "$model"
    done
fi

wait "$ollama_pid"
