#!/usr/bin/env bash
# =============================================================================
# AI News Aggregator - Container Entrypoint
# Handles database migration, healthcheck server, and graceful shutdown
# =============================================================================

set -e

echo "[entrypoint] AI News Aggregator starting..."
echo "[entrypoint] Environment: ${APP_ENV:-development}"

# ---------------------------------------------------------------------------
# Signal handling for graceful shutdown
# ---------------------------------------------------------------------------
shutdown() {
    echo "[entrypoint] Received shutdown signal, stopping gracefully..."
    if [ -n "$APP_PID" ]; then
        kill -TERM "$APP_PID" 2>/dev/null || true
        # Wait up to 30 seconds for clean exit
        for i in $(seq 1 30); do
            if ! kill -0 "$APP_PID" 2>/dev/null; then
                echo "[entrypoint] Process exited cleanly"
                exit 0
            fi
            sleep 1
        done
        echo "[entrypoint] Force killing process..."
        kill -KILL "$APP_PID" 2>/dev/null || true
    fi
    exit 0
}

trap shutdown SIGTERM SIGINT SIGQUIT

# ---------------------------------------------------------------------------
# Wait for dependencies
# ---------------------------------------------------------------------------
wait_for_service() {
    local host="$1"
    local port="$2"
    local name="$3"
    local max_retries="${4:-30}"
    local count=0

    echo "[entrypoint] Waiting for $name at $host:$port..."
    while ! curl -s "http://$host:$port" >/dev/null 2>&1 && ! bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null; do
        count=$((count + 1))
        if [ $count -ge $max_retries ]; then
            echo "[entrypoint] ERROR: $name not available after $max_retries attempts"
            exit 1
        fi
        sleep 2
    done
    echo "[entrypoint] $name is available"
}

# Wait for PostgreSQL
if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
    wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL" 60
fi

# Wait for Redis
if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PORT" ]; then
    wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis" 30
fi

# Wait for Ollama (optional, with shorter timeout)
if [ -n "$OLLAMA_BASE_URL" ]; then
    echo "[entrypoint] Checking Ollama availability at $OLLAMA_BASE_URL..."
    # Extract host:port from URL for check
    OLLAMA_HOST=$(echo "$OLLAMA_BASE_URL" | sed -E 's|https?://([^/:]+).*|\1|')
    OLLAMA_PORT=$(echo "$OLLAMA_BASE_URL" | sed -E 's|https?://[^:]+:([0-9]+).*|\1|')
    OLLAMA_PORT="${OLLAMA_PORT:-11434}"
    # Don't fail if Ollama is down - it's not critical for startup
    count=0
    while ! curl -s "$OLLAMA_BASE_URL/api/tags" >/dev/null 2>&1; do
        count=$((count + 1))
        if [ $count -ge 10 ]; then
            echo "[entrypoint] WARNING: Ollama not available at $OLLAMA_BASE_URL (will retry later)"
            break
        fi
        sleep 3
    done
    if [ $count -lt 10 ]; then
        echo "[entrypoint] Ollama is available"
    fi
fi

# ---------------------------------------------------------------------------
# Database migration
# ---------------------------------------------------------------------------
echo "[entrypoint] Running database migrations..."
cd /app

# Use the init command to create tables
python -m src.main init 2>/dev/null || {
    echo "[entrypoint] WARNING: Database init had issues (tables may already exist)"
}

# ---------------------------------------------------------------------------
# Start lightweight healthcheck HTTP server in background
# ---------------------------------------------------------------------------
python /healthcheck.py &
HEALTH_PID=$!
echo "[entrypoint] Healthcheck server started (PID: $HEALTH_PID)"

# ---------------------------------------------------------------------------
# Start the main application
# ---------------------------------------------------------------------------
echo "[entrypoint] Starting application: $@"

# Execute the CMD
"$@" &
APP_PID=$!

echo "[entrypoint] Application started (PID: $APP_PID)"

# Wait for the application process
wait "$APP_PID"
EXIT_CODE=$?

# Clean up healthcheck
kill "$HEALTH_PID" 2>/dev/null || true

echo "[entrypoint] Application exited with code $EXIT_CODE"
exit $EXIT_CODE