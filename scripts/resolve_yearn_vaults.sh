#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${ENV_NAME:-copilot}"
API_BASE="https://api.yearn.finance/v1/chains/8453/vaults/all"

need_jq() { command -v jq &>/dev/null || (echo "jq non trovato" && exit 1); }
need_gh() { command -v gh &>/dev/null || (echo "gh CLI non trovato" && exit 1); }
need_jq; need_gh

echo "Scarico vaults Yearn per Base (chain 8453)..."
VAULTS_JSON="$(curl -sSfL "$API_BASE" || echo '[]')"

# Mappa: token symbol -> ENV var
declare -A MAP
MAP["USDC"]="YEARN_USDC_VAULT_BASE"
MAP["WETH"]="YEARN_WETH_VAULT_BASE"
MAP["cbBTC"]="YEARN_CBBTC_VAULT_BASE"

found_any=false

for TOKEN in "${!MAP[@]}"; do
  VAR_NAME="${MAP[$TOKEN]}"
  
  # Cerca vault attivo per questo token su Base
  ADDR="$(
    echo "$VAULTS_JSON" | jq -r --arg token "$TOKEN" '
      map(select(.token.symbol == $token))
      | map(select(.endorsed == true))
      | map(select(.version | startswith("3.0") or startswith("2.0")))
      | sort_by(.tvl.tvl) | reverse
      | .[0].address // empty
    '
  )"

  if [[ -n "$ADDR" ]]; then
    found_any=true
    echo "✓ $VAR_NAME = $ADDR"
    if [[ -n "${GITHUB_ENV:-}" ]]; then
      echo "$VAR_NAME=$ADDR" >> "$GITHUB_ENV"
    else
      export "$VAR_NAME=$ADDR"
    fi
    gh variable set "$VAR_NAME" --env "$ENV_NAME" --body "$ADDR" &>/dev/null || echo "  (failed to persist)"
  else
    echo "… non trovato $VAR_NAME per token $TOKEN"
  fi
done

$found_any || echo "Nessun vault Yearn trovato su Base."
