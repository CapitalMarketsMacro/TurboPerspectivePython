#!/usr/bin/env bash
set -e

SOURCE="${1:-solace}"

if [[ "$SOURCE" != "solace" && "$SOURCE" != "nats" ]]; then
    echo "Usage: ./start.sh [solace|nats]"
    exit 1
fi

echo "Starting FX Executions Blotter Server [$SOURCE]..."

if [ -f venv/bin/activate ]; then
    source venv/bin/activate
else
    echo "WARNING: No venv found, using system Python"
fi

if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Copy .env.example to .env and fill in values."
    exit 1
fi

python server.py --source "$SOURCE" &
echo $! > server.pid
echo "Server started with PID $(cat server.pid)"
