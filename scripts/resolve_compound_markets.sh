#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${ENV_NAME:-copilot}"

need_jq() { command -v jq &>/dev/null || (echo "jq non trovato" && exit 1); }
need_gh() { command -v gh &>/dev/null || (echo "gh CLI non trovato" && exit 1); }
need_jq; need_gh

echo "Ricerca mercati Compound V3 (Comet) su Base..."

# Compound V3 - indirizzi ufficiali per Base (chain 8453)
# Fonte: https://docs.compound.finance/collateral-and-borrowing/
declare -A COMET_MARKETS
COMET_MARKETS["USDC"]="0x46e6b214b524310239732D51387075E0e70970bf"  # cUSDCv3 su Base
COMET_MARKETS["USDbC"]="0x9c4ec768c28520B50860ea7a15bd7213a9fF58bf" # cUSDbCv3 su Base (legacy)

for TOKEN in "${!COMET_MARKETS[@]}"; do
  ADDR="${COMET_MARKETS[$TOKEN]}"
  VAR_NAME="COMET_${TOKEN}_MARKET_BASE"
  
  echo "✓ $VAR_NAME = $ADDR"
  if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "$VAR_NAME=$ADDR" >> "$GITHUB_ENV"
  else
    export "$VAR_NAME=$ADDR"
  fi
  gh variable set "$VAR_NAME" --env "$ENV_NAME" --body "$ADDR" &>/dev/null || echo "  (failed to persist)"
done

echo "Ricerca mercati Moonwell (Compound V2 fork) su Base..."

# Moonwell - indirizzi cToken ufficiali per Base
# Fonte: https://docs.moonwell.fi/moonwell/protocol-information/deployed-contracts
declare -A MOONWELL_CTOKENS
MOONWELL_CTOKENS["cbETH"]="0x3bf93770f2d4a794c3d9EBEfBAeBAE2a8f09A5E5"
MOONWELL_CTOKENS["WETH"]="0x628ff693426583D9a7FB391E54366292F509D457"
MOONWELL_CTOKENS["USDC"]="0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22"

for TOKEN in "${!MOONWELL_CTOKENS[@]}"; do
  ADDR="${MOONWELL_CTOKENS[$TOKEN]}"
  VAR_NAME="MOONWELL_${TOKEN}_CTOKEN"
  
  echo "✓ $VAR_NAME = $ADDR"
  if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "$VAR_NAME=$ADDR" >> "$GITHUB_ENV"
  else
    export "$VAR_NAME=$ADDR"
  fi
  gh variable set "$VAR_NAME" --env "$ENV_NAME" --body "$ADDR" &>/dev/null || echo "  (failed to persist)"
done

echo "Compound/Moonwell markets configurati con successo."
