#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Scoring utilities for Attuario Wave Rotation."""

from __future__ import annotations

import os
import time
from typing import Any


def daily_rate(apy: float) -> float:
    """Convert annual APY (decimal) to daily compounded rate."""
    try:
        apy = float(apy)
    except (TypeError, ValueError):
        return 0.0
    if apy <= -0.99:
        return 0.0
    return (1.0 + apy) ** (1.0 / 365.0) - 1.0


def _get_selection(cfg: Any) -> dict:
    if isinstance(cfg, dict):
        return cfg.get("selection", {}) or {}
    return getattr(cfg, "selection", {}) or {}


def _fee_net_daily(pool: dict) -> float:
    perf_bps = pool.get("perfFeeBps") or pool.get("performanceFeeBps") or 0
    mgmt_bps = pool.get("mgmtFeeBps") or pool.get("managementFeeBps") or 0
    try:
        perf = float(perf_bps) / 10000.0
    except (TypeError, ValueError):
        perf = 0.0
    try:
        mgmt = float(mgmt_bps) / 10000.0
    except (TypeError, ValueError):
        mgmt = 0.0
    gross = daily_rate(pool.get("apy", 0.0))
    net = max(0.0, gross * (1.0 - perf) - (mgmt / 365.0))
    return net


def _staleness_penalty(pool: dict, max_age_minutes: float) -> float:
    try:
        age = float(pool.get("apy_age_min") or pool.get("apyAgeMin") or pool.get("updatedMin") or 0)
    except (TypeError, ValueError):
        age = 0.0
    if age <= 0:
        return 0.0
    if age <= max_age_minutes:
        return 0.0
    over = age - max_age_minutes
    return min(0.005, over / 1440.0 * 0.001)  # up to 50 bps


def _tvl_penalty(pool: dict, threshold_usd: float) -> float:
    try:
        tvl = float(pool.get("tvl_usd") or pool.get("tvlUsd") or 0.0)
    except (TypeError, ValueError):
        tvl = 0.0
    if tvl >= threshold_usd:
        return 0.0
    if threshold_usd <= 0:
        return 0.0
    gap = threshold_usd - tvl
    return min(0.003, gap / threshold_usd * 0.003)


def _adapter_penalty(adapter_src: str, penalty: float) -> float:
    if adapter_src.startswith("explicit"):
        return 0.0
    if adapter_src.startswith("auto:"):
        return penalty
    return 0.002  # unknown adapters get a stronger penalty


def normalized_score(pool: dict, *, adapter_src: str, cfg: Any) -> float:
    selection = _get_selection(cfg)
    net_daily = _fee_net_daily(pool)
    if os.getenv("AGGRO_MODE", "").strip().lower() == "true" or selection.get("aggressive"):
        return max(0.0, net_daily)
    staleness_penalty = _staleness_penalty(pool, float(selection.get("max_apy_staleness_min", 60) or 60))
    tvl_penalty = _tvl_penalty(pool, float(selection.get("tvl_penalty_usd", 500000) or 500000))
    adapter_penalty = _adapter_penalty(adapter_src, float(selection.get("adapter_penalty", 0.0001) or 0.0001))
    total_penalty = staleness_penalty + tvl_penalty + adapter_penalty
    return max(0.0, net_daily - total_penalty)


def should_switch(
    best: dict | None,
    current: dict | None,
    *,
    min_delta: float = 0.01,
    cooldown_s: int = 0,
    last_switch_ts: float | None = None,
) -> bool:
    if best is None:
        return False
    if current is None:
        return True
    score_best = float(best.get("score", 0.0))
    score_current = float(current.get("score", 0.0))
    if score_current <= 0:
        return score_best > 0
    # CODEX_RULES: switch if score_new >= score_current * (1 + delta)
    if score_best < score_current * (1.0 + min_delta):
        return False
    if cooldown_s and last_switch_ts:
        if (time.time() - float(last_switch_ts)) < float(cooldown_s):
            return False
    return True
