#!/usr/bin/env bash
# ======================================================
# Controla o processo do worker MQTT (start/stop/status)
# via nohup + PID file — pensado para hospedagem
# compartilhada via cPanel/SSH, sem systemd nem root.
# ======================================================
#
# Uso:
#   ./worker_ctl.sh start
#   ./worker_ctl.sh stop
#   ./worker_ctl.sh restart
#   ./worker_ctl.sh status

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"
VENV_DIR="${WORKER_VENV_DIR:-$BACKEND_DIR/venv}"
PID_FILE="$BACKEND_DIR/worker.pid"
LOG_FILE="$BACKEND_DIR/worker.log"

start() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Worker já está rodando (PID $(cat "$PID_FILE"))."
    exit 0
  fi

  cd "$BACKEND_DIR"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"

  nohup python -m app.worker >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  disown

  echo "Worker iniciado (PID $(cat "$PID_FILE")). Log em $LOG_FILE"
}

stop() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    kill "$(cat "$PID_FILE")"
    rm -f "$PID_FILE"
    echo "Worker interrompido."
  else
    echo "Worker não está rodando (nenhum PID ativo encontrado)."
    rm -f "$PID_FILE"
  fi
}

status() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "ativo (PID $(cat "$PID_FILE"))"
  else
    echo "parado"
  fi
}

case "${1:-}" in
  start)   start ;;
  stop)    stop ;;
  restart) stop; sleep 1; start ;;
  status)  status ;;
  *)
    echo "Uso: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac
