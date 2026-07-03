#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/.." && pwd)"
# shellcheck source=../scripts/dev-ports.sh
source "$REPO_ROOT/scripts/dev-ports.sh"
validate_mockup_ports

RUN_DIR="$ROOT/.run"
PID_FILE="$RUN_DIR/flask.pid"
LOG_FILE="$RUN_DIR/flask.log"
HOST="$MOCKUP_API_HOST"
PORT="$MOCKUP_API_PORT"

mkdir -p "$RUN_DIR"

"$(dirname "$0")/stop.sh" >/dev/null 2>&1 || true

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE")"
  if kill -0 "$old_pid" 2>/dev/null; then
    echo "Mockup API already running (pid=$old_pid). Use scripts/stop.sh first."
    exit 1
  fi
  rm -f "$PID_FILE"
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install uv, then run from yl-scm-mockup-api/:"
  echo "  uv sync"
  exit 1
fi

if [[ ! -d "$ROOT/.venv" ]]; then
  echo "Dependencies not installed. Run from yl-scm-mockup-api/:"
  echo "  uv sync"
  exit 1
fi

cd "$ROOT"
nohup uv run flask --app wsgi:app run --host "$HOST" --port "$PORT" >>"$LOG_FILE" 2>&1 &

pid=$!
echo "$pid" >"$PID_FILE"

for _ in $(seq 1 30); do
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "Mockup API failed to start. Last log lines:"
    tail -20 "$LOG_FILE" 2>/dev/null || true
    rm -f "$PID_FILE"
    exit 1
  fi
  if curl -sf "http://${HOST}:${PORT}/api/v1/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

echo "Mockup API started (pid=$pid)"
echo "  URL:  http://${HOST}:${PORT}/api/v1"
echo "  Log:  $LOG_FILE"
