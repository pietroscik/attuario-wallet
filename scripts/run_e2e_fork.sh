#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${FORK_RPC_URL:-}" ]]; then
  echo "FORK_RPC_URL non impostata"; exit 1
fi

(anvil --fork-url "$FORK_RPC_URL" --chain-id 8453 >/dev/null 2>&1) &
ANVIL_PID=$!
trap 'kill $ANVIL_PID 2>/dev/null || true' EXIT

python3 -m venv .venv-e2e
source .venv-e2e/bin/activate
pip install -r tests/e2e/requirements-e2e.txt
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

# evita il load di plugin di terze parti (es. web3.tools.pytest_ethereum)
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

pytest -m smoke -q
pytest -m fork -q
