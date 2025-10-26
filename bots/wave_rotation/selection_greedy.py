import os
from decimal import Decimal
from pathlib import Path


def _read_number(path: Path, default: float = 0.0) -> float:
    try:
        return float(path.read_text().strip())
    except Exception:
        return default


def eligible_base(pool: dict, cfg: dict) -> bool:
    """Apply only the hard TVL requirement before ranking by return."""

    min_tvl = float(cfg.get("min_tvl_usd", 0) or cfg.get("min_tvl", 0) or 0)
    tvl = pool.get("tvlUsd")
    if min_tvl and tvl is not None and float(tvl) < min_tvl:
        return False

    return True


def why_not(pool: dict, cfg: dict) -> str:
    min_tvl = float(cfg.get("min_tvl_usd", 0) or cfg.get("min_tvl", 0) or 0)
    tvl = pool.get("tvlUsd")
    if min_tvl and tvl is not None and float(tvl) < min_tvl:
        return f"tvl<{min_tvl}"

    return "adapter:none-or-score≤0?"


def net_gain_eur(
    pool: dict,
    *,
    score_curr: float,
    capital_eth: float,
    horizon_hours: float,
    gas_move_est: int,
    w3,
) -> float:
    fx_rate = float(os.getenv("FX_EUR_PER_ETH", "3000"))
    score_new = float(pool.get("score", 0.0))
    edge_eth = max(0.0, score_new - score_curr) * capital_eth * (horizon_hours / 24.0)

    try:
        gas_price_wei = w3.eth.gas_price if w3 is not None else 0  # type: ignore[attr-defined]
    except Exception:
        gas_price_wei = 0
    gas_eth = (gas_move_est * gas_price_wei) / 1e18 if gas_price_wei else 0.0

    pool["net_gain_eth"] = edge_eth - gas_eth
    pool["net_gain_eur"] = pool["net_gain_eth"] * fx_rate
    return pool["net_gain_eur"]


def greedy_rank(ranked: list, current: dict | None, cfg: dict, w3) -> tuple[list, dict | None]:
    selection = cfg.get("selection", {})
    capital_eth = _read_number(Path("bots/wave_rotation/capital.txt"), 0.0)
    score_curr = float((current or {}).get("score", 0.0))
    horizon_hours = float(selection.get("gas_horizon_h", 24) or os.getenv("EDGE_HORIZON_H", 24) or 24)
    gas_move_est = int(os.getenv("GAS_MOVE_EST", "450000") or 450000)

    ranked.sort(
        key=lambda p: net_gain_eur(
            p,
            score_curr=score_curr,
            capital_eth=capital_eth,
            horizon_hours=horizon_hours,
            gas_move_est=gas_move_est,
            w3=w3,
        ),
        reverse=True,
    )
    return ranked, (ranked[0] if ranked else None)


def fallback_if_empty(pools: list, cfg: dict, w3):
    if os.getenv("FORCE_ADAPTER_FALLBACK", "").strip().lower() not in {"1", "true", "yes"}:
        return None

    try:
        from bots.wave_rotation.auto_registry import probe_type
    except Exception:
        return None

    selection = cfg.get("selection", {})
    top_n = int(selection.get("top_n_scan", int(os.getenv("AUTO_TOP_N", "40")) or 40))

    for pool in sorted(pools, key=lambda x: x.get("apy", 0.0), reverse=True)[:top_n]:
        ok, adapter_type, _ = probe_type(w3, pool.get("pool", ""))
        if ok:
            fallback_pool = dict(pool)
            fallback_pool["adapter_source"] = f"auto:{adapter_type}"
            fallback_pool.setdefault("score", 0.0)
            return fallback_pool
    return None
