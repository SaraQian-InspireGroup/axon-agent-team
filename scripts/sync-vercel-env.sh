#!/usr/bin/env bash
# Upload non-sensitive backend env vars to a linked Vercel project.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"

exec "$PYTHON" "$ROOT/scripts/sync_vercel_env.py" --cwd "$ROOT/backend" "$@"
