#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Scoring utilities for Attuario Wave Rotation."""

from __future__ import annotations

import time
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

from constants import DAYS_PER_YEAR, DEFAULT_OPERATIONAL_COST
from time_series_data import collect_pool_time_series


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


# ---------------------------------------------------------------------------
# Trend-aware scoring and net edge estimation
# ---------------------------------------------------------------------------


@dataclass
class TrendWeights:
    w_apy: float = 0.4
    w_trend: float = 0.5
    w_vol: float = 0.05
    w_dd: float = 0.05

    def normalized(self) -> "TrendWeights":
        total = self.w_apy + self.w_trend + self.w_vol + self.w_dd
        if total <= 0:
            return TrendWeights(0.0, 1.0, 0.0, 0.0)
        return TrendWeights(
            self.w_apy / total,
            self.w_trend / total,
            self.w_vol / total,
            self.w_dd / total,
        )

    @staticmethod
    def from_env() -> "TrendWeights":
        return TrendWeights(
            w_apy=float(os.getenv("W_APY", "0.4")),
            w_trend=float(os.getenv("W_TR", "0.5")),
            w_vol=float(os.getenv("W_VOL", "0.05")),
            w_dd=float(os.getenv("W_DD", "0.05")),
        )


@dataclass
class TrendSignalConfig:
    window_days: int = 14
    lookback_days: int = 90
    z_min: float = 0.5
    z_cap: float = 3.0
    vol_cap: float = 0.05
    dd_cap: float = 0.25
    weights: TrendWeights = field(default_factory=TrendWeights)

    @classmethod
    def from_env(cls) -> "TrendSignalConfig":
        window = int(os.getenv("TREND_WINDOW_D", "14"))
        lookback = int(os.getenv("TREND_LOOKBACK_D", str(max(window * 4, 90))))
        return cls(
            window_days=max(3, window),
            lookback_days=max(window * 2, lookback),
            z_min=float(os.getenv("TREND_Z_MIN", "0.5")),
            z_cap=float(os.getenv("TREND_Z_CAP", "3.0")),
            vol_cap=float(os.getenv("TREND_VOL_CAP", "0.05")),
            dd_cap=float(os.getenv("TREND_DD_CAP", "0.25")),
            weights=TrendWeights.from_env(),
        )


@dataclass
class TrendMetrics:
    ok: bool
    trend_z: float = 0.0
    slope: float = 0.0
    volatility: float = 0.0
    max_drawdown: float = 0.0
    rsi: float = 50.0
    sma_fast: float = 0.0
    sma_slow: float = 0.0
    reason: str = ""

    def to_dict(self) -> Dict[str, float]:
        return {
            "trend_z": self.trend_z,
            "slope": self.slope,
            "volatility": self.volatility,
            "max_drawdown": self.max_drawdown,
            "rsi": self.rsi,
            "sma_fast": self.sma_fast,
            "sma_slow": self.sma_slow,
        }

    @staticmethod
    def empty(reason: str = "") -> "TrendMetrics":
        return TrendMetrics(ok=False, reason=reason)


@dataclass
class EdgeConfig:
    horizon_days: float = 1.0
    min_net_usd: float = 0.5
    gas_withdraw_usd: float = 0.35
    gas_deposit_usd: float = 0.35
    swap_fee_bps: float = 5.0
    slippage_bps: float = 50.0

    @classmethod
    def from_env(cls) -> "EdgeConfig":
        return cls(
            horizon_days=float(os.getenv("HORIZON_DAYS", "1.0")),
            min_net_usd=float(os.getenv("EDGE_MIN_NET_USD", "0.5")),
            gas_withdraw_usd=float(os.getenv("GAS_WITHDRAW_COST_USD", "0.35")),
            gas_deposit_usd=float(os.getenv("GAS_DEPOSIT_COST_USD", "0.35")),
            swap_fee_bps=float(os.getenv("SWAP_FEE_BPS", "5.0")),
            slippage_bps=float(os.getenv("EDGE_SLIPPAGE_BPS", os.getenv("SLIPPAGE_BPS", "100"))),
        )


def _compute_rsi(prices: pd.Series, period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    delta = prices.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta.clip(upper=0.0)).abs()
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    valid = rsi.dropna()
    if not len(valid):
        return 50.0
    return float(valid.iloc[-1])


def _max_drawdown(prices: pd.Series) -> float:
    rolling_max = prices.cummax()
    drawdown = 1.0 - prices / (rolling_max.replace(0, np.nan))
    drawdown = drawdown.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return float(drawdown.max())


def compute_trend_metrics(
    pool_id: str,
    pool_data: Dict[str, Any],
    cfg: TrendSignalConfig,
) -> TrendMetrics:
    """Compute trend metrics for a pool using synthetic or fetched data."""
    lookback = max(cfg.lookback_days, cfg.window_days * 3)
    price_series, _, _ = collect_pool_time_series(pool_id, pool_data, lookback)
    price_series = price_series.dropna()
    if len(price_series) < cfg.window_days + 2:
        return TrendMetrics.empty("insufficient_history")

    prices = price_series.astype(float)
    log_prices = np.log(prices.replace(0, np.nan).dropna())
    if len(log_prices) < cfg.window_days + 2:
        return TrendMetrics.empty("insufficient_prices")

    x = np.arange(len(log_prices))
    slope = float(np.polyfit(x, log_prices.values, 1)[0])

    returns = log_prices.diff().dropna()
    vol = float(np.std(returns.tail(cfg.window_days)))
    if not np.isfinite(vol):
        vol = 0.0
    z = slope / (vol if vol > 1e-8 else 1e-8)

    rsi = _compute_rsi(prices, period=min(14, len(prices) - 1))
    sma_fast = float(prices.rolling(cfg.window_days).mean().iloc[-1])
    sma_slow = float(prices.rolling(cfg.window_days * 2).mean().iloc[-1]) if len(prices) >= cfg.window_days * 2 else sma_fast
    drawdown = _max_drawdown(prices)

    return TrendMetrics(
        ok=True,
        trend_z=float(z),
        slope=float(slope),
        volatility=float(vol),
        max_drawdown=float(drawdown),
        rsi=float(rsi),
        sma_fast=sma_fast,
        sma_slow=sma_slow,
    )


def compute_trend_score(
    apy: float,
    metrics: TrendMetrics,
    cfg: TrendSignalConfig,
) -> Tuple[float, Dict[str, float]]:
    weights = cfg.weights.normalized()

    norm_apy = max(0.0, float(apy))
    trend_norm = max(0.0, metrics.trend_z)
    if cfg.z_cap > 0:
        trend_norm = min(trend_norm / cfg.z_cap, 1.0)

    vol_norm = max(0.0, metrics.volatility)
    if cfg.vol_cap > 0:
        vol_norm = min(vol_norm / cfg.vol_cap, 1.0)

    dd_norm = max(0.0, metrics.max_drawdown)
    if cfg.dd_cap > 0:
        dd_norm = min(dd_norm / cfg.dd_cap, 1.0)

    score = (
        weights.w_apy * norm_apy
        + weights.w_trend * trend_norm
        - weights.w_vol * vol_norm
        - weights.w_dd * dd_norm
    )

    return score, {
        "norm_apy": norm_apy,
        "trend_norm": trend_norm,
        "vol_norm": vol_norm,
        "dd_norm": dd_norm,
    }


def net_edge_usd(
    apy: float,
    amount_usd: float,
    cfg: EdgeConfig,
    *,
    include_withdraw: bool = True,
) -> Tuple[float, Dict[str, float]]:
    """Compute expected net edge (in USD) after estimated costs."""
    amount_usd = max(0.0, float(amount_usd))
    horizon_factor = max(cfg.horizon_days, 0.0) / 365.0
    gross = max(0.0, float(apy)) * amount_usd * horizon_factor

    variable_cost = amount_usd * (cfg.swap_fee_bps + cfg.slippage_bps) / 10_000.0
    fixed_cost = cfg.gas_deposit_usd + (cfg.gas_withdraw_usd if include_withdraw else 0.0)
    total_cost = variable_cost + fixed_cost
    net = gross - total_cost

    breakdown = {
        "gross": gross,
        "variable_cost": variable_cost,
        "fixed_cost": fixed_cost,
        "total_cost": total_cost,
    }
    return net, breakdown
