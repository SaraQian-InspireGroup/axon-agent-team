#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Stopping yl-scm-mockup (Vite)..."
"$ROOT/yl-scm-mockup/scripts/stop.sh" || true

echo ""
echo "==> Stopping yl-scm-mockup-api (Flask)..."
"$ROOT/yl-scm-mockup-api/scripts/stop.sh" || true

echo ""
echo "YL SCM Mockup stopped."
