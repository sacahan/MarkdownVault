#!/usr/bin/env bash
# 啟動腳本：會在當前目錄載入 .env（若存在），然後啟動 app.py
# 可覆寫環境變數：例如 PORT、HOST、FORCE_KILL、OPEN_BROWSER、BACKGROUND 等

set -euo pipefail

# --- configuration / defaults -------------------------------------------------
# 預設為前景執行且不自動開啟瀏覽器；使用者可用環境變數覆寫
OPEN_BROWSER="${OPEN_BROWSER:-0}"
BACKGROUND="${BACKGROUND:-0}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-7861}"

export HOST PORT

# --- helpers -----------------------------------------------------------------
load_dotenv() {
  if [ -f .env ]; then
    # 將 .env 中的變數匯入到環境中
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
  fi
}

log() { printf "%s\n" "$*"; }

die() { printf "%s\n" "$*" >&2; exit 1; }

script_dir_and_app_path() {
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  APP_PATH="$(cd "$SCRIPT_DIR/.." && pwd)/app.py"
}

choose_python() {
  # prefer project's .venv, then system python, then python3
  if [ -x "${SCRIPT_DIR:-}/../.venv/bin/python" ]; then
    printf "%s" "${SCRIPT_DIR}/../.venv/bin/python"
  elif command -v python >/dev/null 2>&1; then
    printf "%s" "python"
  elif command -v python3 >/dev/null 2>&1; then
    printf "%s" "python3"
  else
    printf ""
  fi
}

is_port_listening() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -n -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true
  else
    printf ""
  fi
}

kill_pids() {
  for pid in $*; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" || true
    fi
  done
}

wait_for_port_free() {
  local attempts=0
  local max=10
  while [ $attempts -lt $max ]; do
    if [ -z "$(is_port_listening)" ]; then
      return 0
    fi
    sleep 1
    attempts=$((attempts + 1))
  done
  return 1
}

open_browser() {
  local host="$1"
  local url="http://${host}:${PORT}"
  log "Opening browser to $url"
  if command -v open >/dev/null 2>&1; then
    open "$url"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url"
  else
    log "No known command to open browser (tried 'open' and 'xdg-open')." >&2
  fi
}

open_when_ready() {
  local URL="http://$HOST:$PORT"
  local RETRIES=30
  local SLEEP=1
  for i in $(seq 1 $RETRIES); do
    if curl --silent --fail "$URL" >/dev/null 2>&1; then
      if [ "${OPEN_BROWSER:-0}" != "0" ]; then
        local BROWSER_HOST="$HOST"
        if [ "$BROWSER_HOST" = "0.0.0.0" ]; then
          BROWSER_HOST=127.0.0.1
        fi
        open_browser "$BROWSER_HOST"
      fi
      return 0
    fi
    sleep $SLEEP
  done
  log "Server did not respond within timeout; check logs." >&2
  return 1
}

# --- core flow ---------------------------------------------------------------
start_background() {
  local py="$1"
  if command -v uv >/dev/null 2>&1; then
    log "Found 'uv' command — launching in background: uv run $APP_PATH"
    uv run "$APP_PATH" &
  else
    log "Launching in background with: $py $APP_PATH"
    "$py" "$APP_PATH" &
  fi
  SERVER_PID=$!

  if [ -z "${SERVER_PID:-}" ]; then
    die "Failed to start server process."
  fi

  on_signal() {
    sig="$1"
    log "Signal $sig received — forwarding to server pid $SERVER_PID"
    kill -s "$sig" "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
    exit 0
  }
  trap 'on_signal INT' INT
  trap 'on_signal TERM' TERM

  open_when_ready &
  WAITER_PID=$!

  wait "$SERVER_PID"
  # cleanup waiter if still running
  if [ -n "${WAITER_PID:-}" ]; then
    kill -0 "$WAITER_PID" 2>/dev/null && kill "$WAITER_PID" 2>/dev/null || true
  fi
}

start_foreground() {
  local py="$1"
  if [ "${OPEN_BROWSER:-0}" != "0" ]; then
    open_when_ready &
    WAITER_PID=$!
  fi

  if command -v uv >/dev/null 2>&1; then
    log "Found 'uv' command — launching in foreground: uv run $APP_PATH"
    uv run "$APP_PATH"
    EXIT_STATUS=$?
  else
    log "Launching in foreground with: $py $APP_PATH"
    "$py" "$APP_PATH"
    EXIT_STATUS=$?
  fi

  if [ -n "${WAITER_PID:-}" ]; then
    kill -0 "$WAITER_PID" 2>/dev/null && kill "$WAITER_PID" 2>/dev/null || true
  fi

  exit $EXIT_STATUS
}

main() {
  load_dotenv

  log "Starting Markdown Vectorization Service..."
  log "Using Python: $(command -v python || command -v python3)"
  log "Serving at: http://$HOST:$PORT"

  script_dir_and_app_path
  if [ ! -f "$APP_PATH" ]; then
    die "Error: app.py not found at expected path: $APP_PATH"
  fi

  EXISTING_PID_INFO=$(is_port_listening)
  if [ -n "$EXISTING_PID_INFO" ]; then
    log "Port $PORT already in use by PID(s): $EXISTING_PID_INFO"
    if [ "${FORCE_KILL:-0}" = "1" ]; then
      log "FORCE_KILL=1 -> terminating existing process(es): $EXISTING_PID_INFO"
      kill_pids $EXISTING_PID_INFO
      if ! wait_for_port_free; then
        die "Timed out waiting for port $PORT to be freed."
      fi
      log "Port $PORT freed, continuing start."
    else
      log "Port $PORT is in use. To force restart set FORCE_KILL=1."
      if [ "${OPEN_BROWSER:-0}" != "0" ]; then
        BROWSER_HOST="$HOST"
        if [ "$BROWSER_HOST" = "0.0.0.0" ]; then
          BROWSER_HOST=127.0.0.1
        fi
        open_browser "$BROWSER_HOST"
      fi
      exit 0
    fi
  fi

  PY_EXEC=$(choose_python)
  if [ -z "$PY_EXEC" ] && ! command -v uv >/dev/null 2>&1; then
    die "No Python interpreter found (python or python3) and no 'uv' command available. Install Python or create a .venv."
  fi

  if [ "${BACKGROUND:-0}" != "0" ]; then
    start_background "$PY_EXEC"
  else
    start_foreground "$PY_EXEC"
  fi
}

# run
main
