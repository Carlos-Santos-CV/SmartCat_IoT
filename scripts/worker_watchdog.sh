#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$("$SCRIPT_DIR/worker_ctl.sh" status)" != "parado" ]; then
  exit 0
fi

echo "[WATCHDOG $(date '+%Y-%m-%d %H:%M:%S')] Worker parado, reiniciando..." >> "$SCRIPT_DIR/../backend/worker.log"
"$SCRIPT_DIR/worker_ctl.sh" start
