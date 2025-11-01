#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Load environment variables
if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

INTERVAL_SECONDS="${1:-${WAVE_LOOP_INTERVAL_SECONDS:-3600}}"

if ! [[ "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]] || (( INTERVAL_SECONDS < 300 )); then
  echo "Intervallo non valido: usa un numero intero ≥ 300 secondi (5 minuti)." >&2
  exit 1
fi

export WAVE_LOOP_INTERVAL_SECONDS="$INTERVAL_SECONDS"
export PYTHONUNBUFFERED=1

if [[ -d ".venv" ]]; then
  source .venv/bin/activate
fi

LOG_DIR="bots/wave_rotation"
LOG_FILE="$LOG_DIR/daily.log"
RUN_LOG="run.log"

mkdir -p "$LOG_DIR"

echo "[loop] Avvio Wave Rotation (intervallo ${INTERVAL_SECONDS}s). Arresta con Ctrl+C."
echo "[loop] RPC_URL=${RPC_URL:-<non impostata>} | VAULT_ADDRESS=${VAULT_ADDRESS:-<non impostato>}"

run_once() {
  local timestamp
  timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "[$timestamp] ▶︎ Esecuzione strategy.py" | tee -a "$LOG_FILE"
  
  # Run strategy with output to both daily.log and run.log
  python3 -m bots.wave_rotation.strategy --dry-run 2>&1 | tee -a "$LOG_FILE" | tee -a "$RUN_LOG" || \
    echo "[$timestamp] ⚠️ Errore strategy.py (vedi log)" | tee -a "$LOG_FILE" | tee -a "$RUN_LOG"
  
  echo "[$timestamp] ━━ run completa ━━" | tee -a "$LOG_FILE"
}

trap 'echo "[loop] Interrotto, termino."; exit 0' SIGINT SIGTERM

while true; do
  run_once
  sleep "$INTERVAL_SECONDS"
done
