#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SETUP_DIR="$ROOT_DIR/setup"
STATE_DIR="$ROOT_DIR/.aim-runtime"
LOG_DIR="$ROOT_DIR/logs"
SETUP_VENV_DIR="$SETUP_DIR/.venv-linux"
SETUP_REQUIREMENTS="$SETUP_DIR/requirements.txt"

API_PID_FILE="$STATE_DIR/vbox-api.pid"
API_HEALTH_URL="http://127.0.0.1:8090/health"
API_STARTUP_TIMEOUT_SECONDS=20
API_STARTUP_POLL_SECONDS=1

WITH_BACKEND=false
WITH_FRONTEND=false
SKIP_FRONTEND=false

usage() {
    cat <<EOF
Usage: ./setup/start.sh [options]

Options:
  --backend       Start Docker Compose with backend and frontend profiles.
  --no-frontend   Do not start the frontend profile when --backend is used.
  -h, --help      Show this help message.
EOF
}

is_running() {
    local pid_file="$1"

    if [ ! -f "$pid_file" ]; then
        return 1
    fi

    local pid
    pid="$(cat "$pid_file")"

    if [ -z "$pid" ]; then
        return 1
    fi

    kill -0 "$pid" >/dev/null 2>&1
}

system_python_command() {
    if command -v python3 >/dev/null 2>&1; then
        echo "python3"
        return
    fi

    if command -v python >/dev/null 2>&1; then
        echo "python"
        return
    fi

    echo "Python is required but was not found." >&2
    exit 1
}

setup_python_command() {
    local python_bin
    python_bin="$(system_python_command)"

    if [ ! -x "$SETUP_VENV_DIR/bin/python" ]; then
        echo "Creating setup Python virtual environment..." >&2
        "$python_bin" -m venv "$SETUP_VENV_DIR" >&2
    fi

    if [ ! -f "$SETUP_REQUIREMENTS" ]; then
        echo "Missing setup requirements file: $SETUP_REQUIREMENTS" >&2
        exit 1
    fi

    "$SETUP_VENV_DIR/bin/python" -m pip install -r "$SETUP_REQUIREMENTS" >&2
    echo "$SETUP_VENV_DIR/bin/python"
}

api_health_ok() {
    if ! command -v curl >/dev/null 2>&1; then
        echo "curl is required to check the VirtualBox Manager API health." >&2
        return 1
    fi

    curl -fsS "$API_HEALTH_URL" | grep -q '"status":"ok"'
}

show_virtualbox_api_logs() {
    if [ -f "$LOG_DIR/vbox-api.log" ]; then
        echo "VirtualBox Manager API log:"
        tail -n 80 "$LOG_DIR/vbox-api.log"
    fi
}

wait_for_virtualbox_api() {
    local pid="$1"
    local deadline=$((SECONDS + API_STARTUP_TIMEOUT_SECONDS))

    while [ "$SECONDS" -lt "$deadline" ]; do
        if api_health_ok; then
            return 0
        fi

        if ! kill -0 "$pid" >/dev/null 2>&1; then
            return 1
        fi

        sleep "$API_STARTUP_POLL_SECONDS"
    done

    return 1
}

start_virtualbox_api() {
    if is_running "$API_PID_FILE"; then
        local tracked_pid
        tracked_pid="$(cat "$API_PID_FILE")"
        if api_health_ok; then
            echo "VirtualBox Manager API already running (pid $tracked_pid)."
            return
        fi

        echo "VirtualBox Manager API pid $tracked_pid is running, but $API_HEALTH_URL did not respond with status ok." >&2
        exit 1
    fi

    if api_health_ok; then
        echo "VirtualBox Manager API already reachable at $API_HEALTH_URL."
        return
    fi

    local python_bin
    python_bin="$(setup_python_command)"

    echo "Starting VirtualBox Manager API..."
    (
        cd "$ROOT_DIR"
        "$python_bin" -B -m setup.api > "$LOG_DIR/vbox-api.log" 2>&1
    ) &

    echo "$!" > "$API_PID_FILE"
    local api_pid
    api_pid="$(cat "$API_PID_FILE")"

    if wait_for_virtualbox_api "$api_pid"; then
        echo "VirtualBox Manager API started (pid $api_pid)."
        return
    fi

    show_virtualbox_api_logs
    echo "VirtualBox Manager API did not become healthy at $API_HEALTH_URL." >&2
    exit 1
}

start_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        echo "Docker is required but was not found." >&2
        exit 1
    fi

    echo "Starting Docker Compose services..."
    if [ "$WITH_BACKEND" = true ] && [ "$WITH_FRONTEND" = true ]; then
        (
            cd "$ROOT_DIR"
            docker compose --profile backend --profile frontend up -d --build
        )
    elif [ "$WITH_BACKEND" = true ]; then
        (
            cd "$ROOT_DIR"
            docker compose --profile backend up -d --build
        )
    else
        (
            cd "$ROOT_DIR"
            docker compose up -d --build
        )
    fi
}

for arg in "$@"; do
    case "$arg" in
        --backend)
            WITH_BACKEND=true
            ;;
        --no-frontend)
            SKIP_FRONTEND=true
            ;;
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

if [ "$WITH_BACKEND" = true ] && [ "$SKIP_FRONTEND" = false ]; then
    WITH_FRONTEND=true
fi

mkdir -p "$STATE_DIR" "$LOG_DIR"

start_virtualbox_api
start_docker

echo "AIM startup completed."
