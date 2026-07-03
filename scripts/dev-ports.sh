#!/usr/bin/env bash
# 开发环境端口约定 — platform 与 yl-scm-mockup 两套栈互不占用同一端口。
#
# | 栈        | 前端 | 后端 API |
# |-----------|------|----------|
# | Platform  | 5173 | 8000     |
# | Mockup    | 5174 | 5001     |
#
# Mockup 前端内 Nova Chat 仍通过 Vite 代理访问 platform :8000；计划 Tab 直连 mockup API :5001。

# Platform（scripts/start.sh / frontend / backend）
export PLATFORM_BACKEND_HOST="${PLATFORM_BACKEND_HOST:-127.0.0.1}"
export PLATFORM_BACKEND_PORT="${PLATFORM_BACKEND_PORT:-8000}"
export PLATFORM_FRONTEND_HOST="${PLATFORM_FRONTEND_HOST:-127.0.0.1}"
export PLATFORM_FRONTEND_PORT="${PLATFORM_FRONTEND_PORT:-5173}"

# 兼容旧变量名（platform start 脚本仍使用 HOST / PORT / FRONTEND_*）
export HOST="${HOST:-$PLATFORM_BACKEND_HOST}"
export PORT="${PORT:-$PLATFORM_BACKEND_PORT}"
export FRONTEND_HOST="${FRONTEND_HOST:-$PLATFORM_FRONTEND_HOST}"
export FRONTEND_PORT="${FRONTEND_PORT:-$PLATFORM_FRONTEND_PORT}"

# YL SCM Mockup（scripts/start-mockup.sh）
export MOCKUP_API_HOST="${MOCKUP_API_HOST:-127.0.0.1}"
export MOCKUP_API_PORT="${MOCKUP_API_PORT:-5001}"
export MOCKUP_FRONTEND_HOST="${MOCKUP_FRONTEND_HOST:-127.0.0.1}"
export MOCKUP_FRONTEND_PORT="${MOCKUP_FRONTEND_PORT:-5174}"

_reserved_ports() {
  printf '%s\n' \
    "$PLATFORM_BACKEND_PORT" \
    "$PLATFORM_FRONTEND_PORT" \
    "$MOCKUP_API_PORT" \
    "$MOCKUP_FRONTEND_PORT"
}

_assert_distinct_ports() {
  local label="$1"
  shift
  local -a ports=("$@")
  local i j
  for ((i = 0; i < ${#ports[@]}; i++)); do
    for ((j = i + 1; j < ${#ports[@]}; j++)); do
      if [[ "${ports[i]}" == "${ports[j]}" ]]; then
        echo "ERROR: ${label} — port ${ports[i]} is assigned more than once." >&2
        exit 1
      fi
    done
  done
}

validate_all_dev_ports() {
  _assert_distinct_ports "dev port map" \
    "$PLATFORM_BACKEND_PORT" \
    "$PLATFORM_FRONTEND_PORT" \
    "$MOCKUP_API_PORT" \
    "$MOCKUP_FRONTEND_PORT"
}

validate_mockup_ports() {
  validate_all_dev_ports
  if [[ "$MOCKUP_API_PORT" == "$PLATFORM_BACKEND_PORT" ]]; then
    echo "ERROR: MOCKUP_API_PORT ($MOCKUP_API_PORT) must differ from platform backend ($PLATFORM_BACKEND_PORT)." >&2
    exit 1
  fi
  if [[ "$MOCKUP_FRONTEND_PORT" == "$PLATFORM_FRONTEND_PORT" ]]; then
    echo "ERROR: MOCKUP_FRONTEND_PORT ($MOCKUP_FRONTEND_PORT) must differ from platform frontend ($PLATFORM_FRONTEND_PORT)." >&2
    exit 1
  fi
}

validate_platform_ports() {
  validate_all_dev_ports
  if [[ "$PORT" == "$MOCKUP_API_PORT" ]]; then
    echo "ERROR: Platform backend PORT ($PORT) must differ from mockup API ($MOCKUP_API_PORT)." >&2
    exit 1
  fi
  if [[ "$FRONTEND_PORT" == "$MOCKUP_FRONTEND_PORT" ]]; then
    echo "ERROR: Platform frontend FRONTEND_PORT ($FRONTEND_PORT) must differ from mockup frontend ($MOCKUP_FRONTEND_PORT)." >&2
    exit 1
  fi
}

port_owner_hint() {
  local port="$1"
  case "$port" in
    "$PLATFORM_BACKEND_PORT") echo "platform backend (uvicorn)" ;;
    "$PLATFORM_FRONTEND_PORT") echo "platform frontend (vite)" ;;
    "$MOCKUP_API_PORT") echo "yl-scm-mockup-api (flask)" ;;
    "$MOCKUP_FRONTEND_PORT") echo "yl-scm-mockup frontend (vite)" ;;
    *) echo "unknown process" ;;
  esac
}

assert_port_available_or_owned() {
  local port="$1"
  local expected_label="$2"
  local pids
  pids="$(lsof -ti:"$port" 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    return 0
  fi
  echo "WARNING: Port $port already in use ($expected_label expected, may be $(port_owner_hint "$port"))." >&2
  echo "  PIDs: $pids — run ./scripts/stop-mockup.sh or ./scripts/stop.sh if needed." >&2
}
