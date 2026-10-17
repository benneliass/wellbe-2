#!/usr/bin/env bash
# Start, stop, restart, or check the Raw Context Brain lab server.
# Works on macOS and Linux. The lab owns http://localhost:5199.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT=5199
PIDFILE="${ROOT}/.dev-server.pid"
LOGFILE="${ROOT}/.dev-server.log"
URL="http://localhost:${PORT}"

usage() {
  cat <<EOF
Usage: $(basename "$0") {start|stop|restart|status|logs}

  start     Start the lab in the background. Installs dependencies if needed.
  stop      Stop whatever is serving the lab on port ${PORT}.
  restart   Stop, then start.
  status    Print whether the lab is running. Exits 1 when it is not.
  logs      Follow the server log.

Open ${URL} after start.
EOF
}

listening_pids() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN -t 2>/dev/null || true
    return 0
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp "sport = :${PORT}" 2>/dev/null | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' || true
    return 0
  fi
  echo "Need lsof (macOS or Linux) or ss (Linux) to find the process on port ${PORT}." >&2
  exit 1
}

pid_running() {
  local pid="$1"
  [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

stop_server() {
  local pids pid
  pids="$(listening_pids | awk 'NF && !seen[$0]++')"
  if [[ -f "${PIDFILE}" ]]; then
    pid="$(cat "${PIDFILE}" 2>/dev/null || true)"
    if pid_running "${pid}"; then
      pids="$(printf '%s\n%s\n' "${pids}" "${pid}" | awk 'NF && !seen[$0]++')"
    fi
  fi
  if [[ -z "${pids}" ]]; then
    rm -f "${PIDFILE}"
    echo "Lab server is not running."
    return 0
  fi
  echo "Stopping lab server on port ${PORT}..."
  # shellcheck disable=SC2086
  kill ${pids} 2>/dev/null || true
  local attempt
  for attempt in 1 2 3 4 5 6 7 8 9 10; do
    if [[ -z "$(listening_pids)" ]]; then
      break
    fi
    sleep 0.2
  done
  pids="$(listening_pids | awk 'NF && !seen[$0]++')"
  if [[ -n "${pids}" ]]; then
    echo "Still listening; forcing it to stop."
    # shellcheck disable=SC2086
    kill -9 ${pids} 2>/dev/null || true
  fi
  rm -f "${PIDFILE}"
  echo "Stopped."
}

start_server() {
  local pids
  pids="$(listening_pids | awk 'NF && !seen[$0]++' | tr '\n' ' ')"
  if [[ -n "${pids// /}" ]]; then
    echo "Lab server is already running at ${URL} (pid ${pids})"
    return 0
  fi
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm is not on PATH. Install Node.js, then run this script again." >&2
    exit 1
  fi
  if [[ ! -d "${ROOT}/node_modules" ]]; then
    echo "Installing lab dependencies..."
    (cd "${ROOT}" && npm install)
  fi
  echo "Starting lab server at ${URL}"
  (
    cd "${ROOT}"
    nohup npm run dev >"${LOGFILE}" 2>&1 &
    echo $! >"${PIDFILE}"
  )
  local attempt
  for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    if [[ -n "$(listening_pids)" ]]; then
      echo "Ready: ${URL}"
      echo "Log: ${LOGFILE}"
      return 0
    fi
    if [[ -f "${PIDFILE}" ]] && ! pid_running "$(cat "${PIDFILE}")"; then
      echo "The server exited. Last log lines:" >&2
      tail -n 40 "${LOGFILE}" >&2 || true
      rm -f "${PIDFILE}"
      exit 1
    fi
    sleep 0.25
  done
  echo "The server did not open port ${PORT} in time. See ${LOGFILE}" >&2
  exit 1
}

status_server() {
  local pids
  pids="$(listening_pids | awk 'NF && !seen[$0]++' | tr '\n' ' ')"
  if [[ -n "${pids// /}" ]]; then
    echo "Running at ${URL} (pid ${pids})"
    return 0
  fi
  echo "Not running."
  return 1
}

cmd="${1:-}"
case "${cmd}" in
  start) start_server ;;
  stop) stop_server ;;
  restart) stop_server; start_server ;;
  status) status_server ;;
  logs)
    touch "${LOGFILE}"
    tail -n 80 -f "${LOGFILE}"
    ;;
  *)
    usage
    exit 2
    ;;
esac
