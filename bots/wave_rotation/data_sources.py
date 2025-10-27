#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Data providers for the Attuario Wave Rotation strategy."""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List

try:  # Optional dependency – provide graceful degradation in test envs
    import requests
except ModuleNotFoundError:  # pragma: no cover - import guard branch
    requests = None  # type: ignore[assignment]

DEFILLAMA_API = os.getenv("DEFILLAMA_API", "https://yields.llama.fi")


def _safe_get(url: str, *, params: Dict[str, Any] | None = None, timeout: int = 25) -> Dict[str, Any] | None:
    if requests is None:
        print(f"[data] GET {url} skipped: requests not installed")
        return None

    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:  # pragma: no cover - network failure path
        print(f"[data] GET {url} failed: {exc}")
        return None


def _extract_risk(raw: Dict[str, Any]) -> float:
    risk = raw.get("riskFactor") or raw.get("riskScore") or raw.get("risk")
    if isinstance(risk, dict):
        for key in ("score", "value", "riskScore"):
            if risk.get(key) is not None:
                risk = risk[key]
                break
    if isinstance(risk, (int, float)):
        return max(0.0, min(1.0, float(risk)))
    return 0.0


def _extract_fee(raw: Dict[str, Any]) -> float:
    fee = raw.get("fee") or raw.get("managementFee") or raw.get("performanceFee")
    if isinstance(fee, str):
        fee = fee.strip("% ")
        try:
            fee = float(fee) / 100.0
        except ValueError:
            fee = None
    if isinstance(fee, (int, float)):
        return max(0.0, float(fee))
    # default operational cost baseline (5 bps)
    return 0.0005


def _normalize_defillama_pool(raw: Dict[str, Any]) -> Dict[str, Any]:
    apy = raw.get("apy")
    apy = float(apy) if isinstance(apy, (int, float)) else 0.0
    tvl = raw.get("tvlUsd")
    tvl = float(tvl) if isinstance(tvl, (int, float)) else 0.0

    project = raw.get("project", "unknown")
    symbol = raw.get("symbol") or raw.get("tokens") or ""
    chain = raw.get("chain", "unknown").lower()
    pool_address = raw.get("pool") or raw.get("address") or ""

    pool_id = f"{chain}:{project}:{symbol or pool_address}"

    return {
        "pool_id": pool_id,
        "chain": chain,
        "name": f"{project}-{symbol}".strip("-"),
        "apy": apy / 100.0 if apy > 2 else apy,  # API sometimes returns % (0-100); normalise to decimal
        "tvl_usd": tvl,
        "risk_score": _extract_risk(raw),
        "fee_pct": _extract_fee(raw),
        "symbol": symbol,
        "project": project,
        "address": pool_address,
    }


def fetch_defillama_pools(chains: Iterable[str]) -> List[Dict[str, Any]]:
    url = f"{DEFILLAMA_API.rstrip('/')}/pools"
    payload = _safe_get(url)
    if not payload or "data" not in payload:
        return []

    chains_lower = {c.lower() for c in chains}
    pools: List[Dict[str, Any]] = []
    for raw in payload["data"]:
        chain = (raw.get("chain") or "").lower()
        if chains_lower and chain not in chains_lower:
            continue
        pools.append(_normalize_defillama_pool(raw))
    return pools


def fetch_protocol_api(_names: Iterable[str]) -> List[Dict[str, Any]]:
    """Placeholder for protocol-specific enrichments (Aerodrome, Velodrome, Kamino, ...)."""
    # Integrations can add richer risk/cost data; return empty for now.
    return []


def fetch_pools(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    pools: List[Dict[str, Any]] = []
    sources = config.get("sources", {})

    if sources.get("defillama", True):
        pools.extend(fetch_defillama_pools(config.get("chains", [])))

    proto_sources = sources.get("protocol_apis", [])
    if proto_sources:
        pools.extend(fetch_protocol_api(proto_sources))

    # deduplicate by pool_id keeping highest TVL entry
    dedup: Dict[str, Dict[str, Any]] = {}
    for pool in pools:
        current = dedup.get(pool["pool_id"])
        if not current or pool["tvl_usd"] > current["tvl_usd"]:
            dedup[pool["pool_id"]] = pool
    return list(dedup.values())


def fetch_pools_scoped(config: Dict[str, Any]):
    pools = fetch_pools(config)
    scope = config.get("search_scope", "GLOBAL")
    meta = {"count": len(pools), "scope": scope}
    return pools, "defillama", meta
