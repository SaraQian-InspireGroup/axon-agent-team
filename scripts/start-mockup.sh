#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=dev-ports.sh
source "$ROOT/scripts/dev-ports.sh"
validate_mockup_ports

echo "==> Starting yl-scm-mockup-api (Flask)..."
"$ROOT/yl-scm-mockup-api/scripts/start.sh"

API_HOST="${MOCKUP_API_HOST}"
API_PORT="${MOCKUP_API_PORT}"
echo "==> Verifying mockup API..."
for _ in $(seq 1 30); do
  if curl -sf "http://${API_HOST}:${API_PORT}/api/v1/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

echo ""
echo "==> Starting yl-scm-mockup (Vite)..."
"$ROOT/yl-scm-mockup/scripts/start.sh"

echo ""
echo "YL SCM Mockup is up."
echo "  Frontend:   http://${MOCKUP_FRONTEND_HOST}:${MOCKUP_FRONTEND_PORT}"
echo "  Mockup API: http://${MOCKUP_API_HOST}:${MOCKUP_API_PORT}/api/v1"
echo "  Health:     http://${MOCKUP_API_HOST}:${MOCKUP_API_PORT}/api/v1/health"
echo ""
echo "Platform (Nova) uses separate ports — no conflict:"
echo "  Platform FE: http://${PLATFORM_FRONTEND_HOST}:${PLATFORM_FRONTEND_PORT}"
echo "  Platform BE: http://${PLATFORM_BACKEND_HOST}:${PLATFORM_BACKEND_PORT}"
