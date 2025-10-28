#!/usr/bin/env bash
# Risolve Yearn v3 su Base (8453) per USDC/WETH via yDaemon con priorità & fallback
set -euo pipefail

CHAIN_ID="${YEARN_CHAIN_ID:-8453}"
API_BASE="${YEARN_API_BASE:-https://ydaemon.yearn.fi}"
URL="${API_BASE}/${CHAIN_ID}/vaults/all?strategiesDetails=noDetails"

echo "Scarico vaults Yearn per chain ${CHAIN_ID} da ${API_BASE}..."

JSON="$(curl -m 20 --retry 2 --retry-delay 1 -fsSL "$URL" || true)"
if [[ -z "${JSON}" ]]; then
  echo "Errore: impossibile scaricare da ${URL}" >&2
  return 1 2>/dev/null || exit 1
fi

# USDC / USDbC → preferisci Horizon > Fluid > Moonwell (+1 se version==3)
usdc_addr="$(jq -r '
  [ .[] 
    | { address: .address
      , name:    (.name // "")
      , ver:     (.version // "")
      , share:   (.token.symbol // "")
      , u:       (.underlyingToken.symbol // .asset.symbol // .token.underlying.symbol // "")
      }
    | select(
        (.u     | test("(?i)^USDC$|^USDbC$")) or
        (.share | test("(?i)USDC")) or
        (.name  | test("(?i)USDC|USDbC"))
      )
    | .score = (
        (if (.name | test("(?i)Horizon")) then 3 else 0 end) +
        (if (.name | test("(?i)Fluid"))   then 2 else 0 end) +
        (if (.name | test("(?i)Moonwell"))then 1 else 0 end) +
        (if (.ver == "3")                 then 1 else 0 end)
      )
  ] | sort_by(.score) | reverse | .[0].address // empty
' <<< "$JSON")"

# WETH → preferisci ysWETH > Meta/Morpho (+1 se version==3)
weth_addr="$(jq -r '
  [ .[] 
    | { address: .address
      , name:    (.name // "")
      , ver:     (.version // "")
      , share:   (.token.symbol // "")
      , u:       (.underlyingToken.symbol // .asset.symbol // .token.underlying.symbol // "")
      }
    | select(
        (.u     | test("(?i)^WETH$")) or
        (.share | test("(?i)WETH")) or
        (.name  | test("(?i)WETH|ysWETH|Morpho|Meta"))
      )
    | .score = (
        (if (.share | test("(?i)^ysWETH$"))      then 3 else 0 end) +
        (if (.name  | test("(?i)Morpho|Meta"))   then 2 else 0 end) +
        (if (.ver == "3")                        then 1 else 0 end)
      )
  ] | sort_by(.score) | reverse | .[0].address // empty
' <<< "$JSON")"

emit () {
  local key="$1" val="$2"
  echo "${key}=${val}"
  export "${key}=${val}"
  if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "${key}=${val}" >> "$GITHUB_ENV"
  fi
}
ok() { [[ -n "${1:-}" ]]; }

if ok "$usdc_addr"; then
  emit YEARN_USDC_VAULT_BASE "$usdc_addr"
else
  echo "… non trovato YEARN_USDC_VAULT_BASE (USDC/USDbC su ${CHAIN_ID})" >&2
fi

if ok "$weth_addr"; then
  emit YEARN_WETH_VAULT_BASE "$weth_addr"
else
  echo "… non trovato YEARN_WETH_VAULT_BASE (WETH su ${CHAIN_ID})" >&2
fi

# Debug opzionale: suggerisci candidati
if ! ok "$usdc_addr"; then
  echo "--- Possibili USDC/USDbC (top 5) ---"
  jq -r '
    [ .[] 
      | { address: .address
        , name:    (.name // "")
        , ver:     (.version // "")
        , share:   (.token.symbol // "")
        , u:       (.underlyingToken.symbol // .asset.symbol // .token.underlying.symbol // "")
        }
      | select(
          (.u     | test("(?i)^USDC$|^USDbC$")) or
          (.share | test("(?i)USDC")) or
          (.name  | test("(?i)USDC|USDbC|Horizon|Fluid|Moonwell"))
        )
      | .score = (
          (if (.name | test("(?i)Horizon")) then 3 else 0 end) +
          (if (.name | test("(?i)Fluid"))   then 2 else 0 end) +
          (if (.name | test("(?i)Moonwell"))then 1 else 0 end) +
          (if (.ver == "3")                 then 1 else 0 end)
        )
    ] | sort_by(.score) | reverse
      | .[0:5][] | "\(.name) | share=\(.share) | u=\(.u) | v\(.ver) | \(.address)"
  ' <<< "$JSON" || true
fi

if ! ok "$weth_addr"; then
  echo "--- Possibili WETH (top 5) ---"
  jq -r '
    [ .[] 
      | { address: .address
        , name:    (.name // "")
        , ver:     (.version // "")
        , share:   (.token.symbol // "")
        , u:       (.underlyingToken.symbol // .asset.symbol // .token.underlying.symbol // "")
        }
      | select(
          (.u     | test("(?i)^WETH$")) or
          (.share | test("(?i)WETH")) or
          (.name  | test("(?i)WETH|ysWETH|Morpho|Meta"))
        )
      | .score = (
          (if (.share | test("(?i)^ysWETH$"))      then 3 else 0 end) +
          (if (.name  | test("(?i)Morpho|Meta"))   then 2 else 0 end) +
          (if (.ver == "3")                        then 1 else 0 end)
        )
    ] | sort_by(.score) | reverse
      | .[0:5][] | "\(.name) | share=\(.share) | u=\(.u) | v\(.ver) | \(.address)"
  ' <<< "$JSON" || true
fi

echo "Yearn vaults risolti (se disponibili)."
