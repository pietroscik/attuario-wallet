#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Scoring utilities for Attuario Wave Rotation."""

from __future__ import annotations

import time
from typing import Any

from constants import DAYS_PER_YEAR, DEFAULT_OPERATIONAL_COST


def daily_rate(apy: float) -> float:
    """Convert annual APY (decimal) to daily compounded rate."""
    try:
        apy = float(apy)
    except (TypeError, ValueError):
        return 0.0
    if apy <= -0.99:
        return 0.0
    return (1.0 + apy) ** (1.0 / DAYS_PER_YEAR) - 1.0


def _extract_cost(pool: dict) -> float:
    """Return the operational cost for the day as a decimal."""

    value = pool.get("fee_pct")
    try:
        annual_cost = max(0.0, float(value)) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0

    # DefiLlama exposes fees as annual percentages. Convert to a daily cost so the
    # score operates on the same time basis as the APY-derived return.
    return annual_cost / DAYS_PER_YEAR


def daily_cost(pool: dict) -> float:
    """Public helper returning the daily operational cost."""

    return _extract_cost(pool)


def _extract_risk(pool: dict) -> float:
    value = pool.get("risk_score") or pool.get("risk") or 0.0
    try:
        risk = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, risk))


def normalized_score(pool: dict, *, adapter_src: str = "", cfg: Any | None = None) -> float:
    """Return the pool score following CODEX_RULES."""

    del adapter_src, cfg  # metadata no longer affects the score

    r_day = daily_rate(pool.get("apy", 0.0))
    if r_day <= 0:
        return r_day

    cost = _extract_cost(pool)
    risk = _extract_risk(pool)
    denominator = 1.0 + cost * (1.0 - risk)
    return r_day / denominator if denominator > 0 else 0.0


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
