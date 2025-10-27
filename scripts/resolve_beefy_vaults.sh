#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${ENV_NAME:-copilot}"   # environment GitHub
API="https://api.beefy.finance/vaults"

need_jq() { command -v jq &>/dev/null || (echo "jq non trovato" && exit 1); }
need_gh() { command -v gh &>/dev/null || (echo "gh CLI non trovato" && exit 1); }
need_jq; need_gh

echo "Scarico vaults Beefy..."
VAULTS_JSON="$(curl -sSfL "$API")"

# mappa: [pattern id/asset] -> ENV var da impostare
declare -A MAP
MAP["USDC-USDT"]="BEEFY_USDC_USDT_VAULT"
MAP["WETH-USDC"]="BEEFY_WETH_USDC_VAULT"
MAP["WETH-USDT"]="BEEFY_WETH_USDT_VAULT"
MAP["cbETH-WETH"]="BEEFY_CBETH_WETH_VAULT"

found_any=false

for KEY in "${!MAP[@]}"; do
  VAR_NAME="${MAP[$KEY]}"

  # match robusto: chain=base, active, piattaforma aerodrome/CL, id o assets contenenti le due legs
  ADDR="$(
    echo "$VAULTS_JSON" | jq -r --arg k "$KEY" '
      map(select(.chain=="base"))
      | map(select((.status//"active")!="eol"))
      | map(select((.platform//"")|test("aero|aerodrome|cow","i")))
      | map(select(
          ((.id//"")|test(($k|sub("-";".*")), "i"))
          or ((.assets//[])|join("-")|test($k,"i"))
        ))
      | .[0].earnContractAddress // empty
    '
  )"

  if [[ -n "$ADDR" ]]; then
    found_any=true
    echo "✓ $VAR_NAME = $ADDR"
    # Valorizza per QUESTA run
    echo "$VAR_NAME=$ADDR" >> "$GITHUB_ENV"
    # Salva anche come GitHub Environment Variable (per le run future)
    gh variable set "$VAR_NAME" --env "$ENV_NAME" --body "$ADDR" &>/dev/null || echo "  (failed to persist via gh variable)"
  else
    echo "… non trovato $VAR_NAME (KEY=$KEY), lascio vuoto"
  fi
done

$found_any || echo "Nessun vault trovato (controlla filtri/KEY)."
