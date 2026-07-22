#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$ROOT_DIR/.aim-runtime"

API_PID_FILE="$STATE_DIR/vbox-api.pid"

usage() {
    cat <<EOF
Usage: ./setup/stop.sh [options]

Options:
  -h, --help      Show this help message.
EOF
}

for arg in "$@"; do
    case "$arg" in
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            usage
            exit 1
            ;;
    esac
done

stop_pid_file() {
    local name="$1"
    local pid_file="$2"

    if [ ! -f "$pid_file" ]; then
        echo "$name is not tracked."
        return
    fi

    local pid
    pid="$(cat "$pid_file")"

    if [ -z "$pid" ]; then
        rm -f "$pid_file"
        echo "$name pid file was empty."
        return
    fi

    if kill -0 "$pid" >/dev/null 2>&1; then
        echo "Stopping $name (pid $pid)..."
        kill "$pid" >/dev/null 2>&1 || true
    else
        echo "$name was not running."
    fi

    rm -f "$pid_file"
}

stop_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        echo "Docker not found. Skipping Docker Compose shutdown."
        return
    fi

    echo "Stopping Docker Compose services..."
    (
        cd "$ROOT_DIR"
        docker compose --profile backend --profile frontend down
    )
}

stop_docker
stop_pid_file "VirtualBox Manager API" "$API_PID_FILE"

echo "AIM shutdown completed."
