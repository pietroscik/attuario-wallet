#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""High-level helpers to query Aerodrome Slipstream pools for strategy ranking."""
from __future__ import annotations
from typing import Dict, List, Optional
from .graph_client import graph_query

SLIPSTREAM_RANKING_QUERY = """
query SlipstreamRanking($limit: Int!) {
  poolDayDatas(
    first: $limit,
    orderBy: volumeUSD,
    orderDirection: desc,
    where: { pool_: { protocol: "slipstream" } }
  ) {
    date
    volumeUSD
    tvlUSD
    pool {
      id
      feeTier
      token0 { id symbol decimals }
      token1 { id symbol decimals }
      liquidity
      sqrtPrice
      tick
    }
  }
}
"""

POOL_DETAILS_QUERY = """
query PoolDetails($id: ID!) {
  pool(id: $id) {
    id
    feeTier
    liquidity
    sqrtPrice
    tick
    volumeUSD
    tvlUSD
    token0 { id symbol decimals }
    token1 { id symbol decimals }
  }
}
"""

def fetch_slipstream_rankings(limit: int = 12) -> List[Dict[str, float]]:
    """Return enriched metrics for the top Slipstream pools."""
    document = graph_query(SLIPSTREAM_RANKING_QUERY, variables={"limit": limit})
    result: List[Dict[str, float]] = []
    for item in document.get("data", {}).get("poolDayDatas", []):
        pool = item.get("pool") or {}
        entry = {
            "pool_id": pool.get("id"),
            "fee_tier": pool.get("feeTier"),
            "volume_usd": float(item.get("volumeUSD") or 0.0),
            "tvl_usd": float(item.get("tvlUSD") or 0.0),
            "token0_symbol": (pool.get("token0") or {}).get("symbol"),
            "token1_symbol": (pool.get("token1") or {}).get("symbol"),
            "token0_address": (pool.get("token0") or {}).get("id"),
            "token1_address": (pool.get("token1") or {}).get("id"),
            "token0_decimals": (pool.get("token0") or {}).get("decimals"),
            "token1_decimals": (pool.get("token1") or {}).get("decimals"),
        }
        result.append(entry)
    return result

def fetch_pool_details(pool_id: str) -> Optional[Dict[str, float]]:
    """Fetch detailed metrics for a specific Slipstream pool."""
    if not pool_id:
        return None
    document = graph_query(POOL_DETAILS_QUERY, variables={"id": pool_id})
    pool = document.get("data", {}).get("pool")
    if not pool:
        return None
    return {
        "pool_id": pool.get("id"),
        "fee_tier": pool.get("feeTier"),
        "volume_usd": float(pool.get("volumeUSD") or 0.0),
        "tvl_usd": float(pool.get("tvlUSD") or 0.0),
        "liquidity": float(pool.get("liquidity") or 0.0),
        "sqrt_price": float(pool.get("sqrtPrice") or 0.0),
        "tick": float(pool.get("tick") or 0.0),
        "token0_symbol": (pool.get("token0") or {}).get("symbol"),
        "token1_symbol": (pool.get("token1") or {}).get("symbol"),
    }
