#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN_DIR="$ROOT/.run"
PID_FILE="$RUN_DIR/uvicorn.pid"
LOG_FILE="$RUN_DIR/uvicorn.log"
VENV="$ROOT/.venv"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

mkdir -p "$RUN_DIR"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE")"
  if kill -0 "$old_pid" 2>/dev/null; then
    echo "Backend already running (pid=$old_pid). Use scripts/stop.sh first."
    exit 1
  fi
  rm -f "$PID_FILE"
fi

if [[ ! -x "$VENV/bin/uvicorn" ]]; then
  echo "Virtualenv not found. Run from backend/:"
  echo "  python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'"
  exit 1
fi

cd "$ROOT"
nohup "$VENV/bin/uvicorn" app.main:app \
  --host "$HOST" \
  --port "$PORT" \
  >>"$LOG_FILE" 2>&1 &

pid=$!
echo "$pid" >"$PID_FILE"

ready=0
for _ in $(seq 1 40); do
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "Backend failed to start. Last log lines:"
    tail -20 "$LOG_FILE" 2>/dev/null || true
    rm -f "$PID_FILE"
    exit 1
  fi
  if curl -sf "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 0.5
done

if [[ "$ready" -ne 1 ]]; then
  echo "Backend did not become healthy in time. Last log lines:"
  tail -20 "$LOG_FILE" 2>/dev/null || true
  kill "$pid" 2>/dev/null || true
  rm -f "$PID_FILE"
  exit 1
fi

echo "Backend started (pid=$pid)"
echo "  URL:  http://${HOST}:${PORT}"
echo "  Log:  $LOG_FILE"
