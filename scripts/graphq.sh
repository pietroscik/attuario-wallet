#!/usr/bin/env bash
set -euo pipefail

URL="${AERODROME_API:?missing AERODROME_API}"
QUERY="${1:?missing GraphQL query}"
VARS="${2:-null}"

curl -sS -H "content-type: application/json" \
  --data "{\"query\":\"${QUERY}\",\"variables\":${VARS}}" \
  "$URL"
