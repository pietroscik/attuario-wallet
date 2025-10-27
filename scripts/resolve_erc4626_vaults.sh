#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${ENV_NAME:-copilot}"

need_jq() { command -v jq &>/dev/null || (echo "jq non trovato" && exit 1); }
need_gh() { command -v gh &>/dev/null || (echo "gh CLI non trovato" && exit 1); }
need_jq; need_gh

echo "Ricerca vault ERC-4626 su Base..."

# ERC-4626 vault addresses per Base
# Morpho Blue vaults e altri vault standard
declare -A ERC4626_VAULTS
ERC4626_VAULTS["USDC"]="0xef417a2512C5a41f69AE4e021648b69a7CdE5D03"  # Morpho USDC vault
ERC4626_VAULTS["WETH"]="0x38989BBA00BDF8181F4082995b3DEAe96163aC5D"  # Gauntlet WETH Core (Base)
ERC4626_VAULTS["cbBTC"]=""  # Da configurare manualmente se disponibile

for TOKEN in "${!ERC4626_VAULTS[@]}"; do
  ADDR="${ERC4626_VAULTS[$TOKEN]}"
  if [[ -z "$ADDR" ]]; then
    echo "… ${TOKEN}_ERC4626_VAULT non disponibile"
    continue
  fi
  
  VAR_NAME="${TOKEN}_ERC4626_VAULT"
  
  echo "✓ $VAR_NAME = $ADDR"
  if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "$VAR_NAME=$ADDR" >> "$GITHUB_ENV"
  else
    export "$VAR_NAME=$ADDR"
  fi
  gh variable set "$VAR_NAME" --env "$ENV_NAME" --body "$ADDR" &>/dev/null || echo "  (failed to persist)"
done

echo "ERC-4626 vaults configurati."
