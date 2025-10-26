#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".env" ]]; then
  # shellcheck disable=SC1091
  source .env
fi

source .venv/bin/activate
python3 bots/wave_rotation/strategy.py >> bots/wave_rotation/daily.log 2>&1
