#!/usr/bin/env bash
set -euo pipefail
export CODEX=1
export PYTHONUNBUFFERED=1
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/mpl}"; mkdir -p "$MPLCONFIGDIR"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r bots/wave_rotation/requirements.txt

: "${DATA_SOURCE_MODE:=PREFER_CACHE}"
: "${PORTFOLIO_DRY_RUN:=true}"
: "${ONCHAIN_ENABLED:=false}"
export DATA_SOURCE_MODE PORTFOLIO_DRY_RUN ONCHAIN_ENABLED

# Diagnostica minima (non stampa segreti)
python3 - <<'PY'
import os
for k in ["RPC_URL","RPC_FALLBACKS","ALCHEMY_API_KEY","PRIVATE_KEY","VAULT_ADDRESS","TELEGRAM_TOKEN","TELEGRAM_CHATID"]:
    print(f"{k}: {'SET' if os.getenv(k) else 'MISSING'}")
PY

python3 bots/wave_rotation/strategy.py --print-status
