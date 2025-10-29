#!/usr/bin/env bash
# Risolve Yearn v3 su Base (8453) per USDC/WETH via yDaemon con priorità & fallback
set -euo pipefail

CHAIN_ID="${YEARN_CHAIN_ID:-8453}"
API_BASE="${YEARN_API_BASE:-https://ydaemon.yearn.fi}"
URL="${API_BASE}/${CHAIN_ID}/vaults/all?strategiesDetails=noDetails"

echo "Scarico vaults Yearn per chain ${CHAIN_ID} da ${API_BASE}..."

JSON="$(curl -m 20 --retry 2 --retry-delay 1 -fsSL "$URL" || true)"
if [[ -z "${JSON}" ]]; then
  echo "WARN: impossibile scaricare da ${URL}, uso solo fallback locali" >&2
  JSON='[]'
fi

# Fallback statici (nel caso l'API non risponda)
FALLBACK_USDC="0xc3BD0A2193c8F027B82ddE3611D18589ef3f62a9"
FALLBACK_WETH="0x7c0Fa3905B38D44C0F29150FD61f182d1e097EC2"
FALLBACK_CBBTC="0x25f32eC89ce7732A4E9f8F3340a09259F823b7d3"

# Helper per assegnare uno score e recuperare i vault
find_addr() {
  local symbol_regex="$1"
  local name_regex="$2"
  jq -r --arg sym "$symbol_regex" --arg name "$name_regex" '
    [ .[] 
      | { address: .address
        , name:    (.name // "")
        , ver:     (.version // "")
        , share:   (.token.symbol // "")
        , u:       (.underlyingToken.symbol // .asset.symbol // .token.underlying.symbol // "")
      }
      | select(
          (.u     | test($sym; "i")) or
          (.share | test($name; "i")) or
          (.name  | test($name; "i"))
        )
      | .score = (
          (if (.ver == "3") then 1 else 0 end) +
          (if (.name | test($name; "i")) then 1 else 0 end)
        )
    ] | sort_by(.score) | reverse | .[0].address // empty
  ' <<< "$JSON"
}

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

# cbBTC → vault Coinbase/Multi strategy (fallback statico)
cbbtc_addr="$(find_addr "^cbBTC$" "cbBTC|coinbase")"

emit () {
  local key="$1" val="$2"
  echo "${key}=${val}"
  export "${key}=${val}"
  if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "${key}=${val}" >> "$GITHUB_ENV"
  fi
}
ok() { [[ -n "${1:-}" ]]; }

if ! ok "$usdc_addr"; then
  echo "WARN: USDC Yearn vault non trovato via API, uso fallback $FALLBACK_USDC" >&2
  usdc_addr="$FALLBACK_USDC"
fi

if ! ok "$weth_addr"; then
  echo "WARN: WETH Yearn vault non trovato via API, uso fallback $FALLBACK_WETH" >&2
  weth_addr="$FALLBACK_WETH"
fi

if ! ok "$cbbtc_addr"; then
  echo "WARN: cbBTC Yearn vault non trovato via API, uso fallback $FALLBACK_CBBTC" >&2
  cbbtc_addr="$FALLBACK_CBBTC"
fi

emit YEARN_USDC_VAULT_BASE "$usdc_addr"
emit YEARN_WETH_VAULT_BASE "$weth_addr"
emit YEARN_CBBTC_VAULT_BASE "$cbbtc_addr"

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

if ! ok "$cbbtc_addr"; then
  echo "--- Possibili cbBTC (top 5) ---"
  jq -r '
    [ .[] 
      | { address: .address
        , name:    (.name // "")
        , ver:     (.version // "")
        , share:   (.token.symbol // "")
        , u:       (.underlyingToken.symbol // .asset.symbol // .token.underlying.symbol // "")
      }
      | select(
          (.u     | test("(?i)^cbBTC$") ) or
          (.share | test("(?i)cbBTC")) or
          (.name  | test("(?i)cbBTC|coinbase"))
        )
      | .score = (
          (if (.name | test("(?i)coinbase")) then 2 else 0 end) +
          (if (.ver == "3")                 then 1 else 0 end)
        )
    ] | sort_by(.score) | reverse
      | .[0:5][] | "\(.name) | share=\(.share) | u=\(.u) | v\(.ver) | \(.address)"
  ' <<< "$JSON" || true
fi

echo "Yearn vaults risolti (se disponibili)."
