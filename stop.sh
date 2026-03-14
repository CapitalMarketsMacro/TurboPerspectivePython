#!/usr/bin/env bash
set -e

echo "Stopping FX Executions Blotter Server..."

if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "Sent SIGTERM to PID $PID"
        rm -f server.pid
    else
        echo "Process $PID not running, cleaning up stale pid file"
        rm -f server.pid
    fi
else
    echo "No server.pid found, attempting to find process on port 8080..."
    PID=$(lsof -ti :8080 2>/dev/null || true)
    if [ -n "$PID" ]; then
        kill "$PID"
        echo "Sent SIGTERM to PID $PID"
    else
        echo "No server process found"
    fi
fi

echo "Done."
