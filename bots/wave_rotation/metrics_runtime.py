# -*- coding: utf-8 -*-
"""
Metrics runtime adattive alla durata del loop.
- Sceglie finestre EMA/isteresi in base a LOOP_INTERVAL (minuti)
- Calcola: EMA_fast/slow, slope su EMA_slow (trend), TWR/log-return,
  downside stdev, max drawdown, ΔTVL/ΔAPY coerenti con la granularità
- Genera segnali UP/HOLD/DOWN con isteresi
"""

from dataclasses import dataclass
from math import prod, log
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd


# ---------- Profili adattivi per finestra in base al loop ----------
@dataclass
class LoopProfile:
    loop_minutes: int
    resample_rule: str          # '5min', '15min', '60min', '1D'
    ema_fast_bars: int
    ema_slow_bars: int
    confirm_bars_in: int        # isteresi ingresso
    confirm_bars_out: int       # isteresi uscita
    dd_stop: float              # stop su drawdown locale (0-1)
    vol_cap: float              # cap su downside deviation (filtro)


def _choose_profile(loop_minutes: int) -> LoopProfile:
    m = max(1, int(loop_minutes))
    if m <= 5:
        return LoopProfile(
            loop_minutes=m, resample_rule="5min",
            ema_fast_bars=12, ema_slow_bars=36,
            confirm_bars_in=2, confirm_bars_out=1,
            dd_stop=0.15, vol_cap=0.025
        )
    if m <= 15:
        return LoopProfile(
            loop_minutes=m, resample_rule="15min",
            ema_fast_bars=12, ema_slow_bars=48,
            confirm_bars_in=2, confirm_bars_out=1,
            dd_stop=0.18, vol_cap=0.03
        )
    if m <= 60:
        return LoopProfile(
            loop_minutes=m, resample_rule="60min",
            ema_fast_bars=24, ema_slow_bars=96,
            confirm_bars_in=1, confirm_bars_out=1,
            dd_stop=0.20, vol_cap=0.035
        )
    # daily or slower
    return LoopProfile(
        loop_minutes=m, resample_rule="1D",
        ema_fast_bars=7, ema_slow_bars=30,
        confirm_bars_in=1, confirm_bars_out=1,
        dd_stop=0.22, vol_cap=0.04
    )


# ---------- Indicatori di base ----------
def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()

def log_returns(series: pd.Series) -> pd.Series:
    return np.log(series/series.shift(1))

def max_drawdown(nav: pd.Series) -> float:
    rollmax = nav.cummax()
    dd = 1.0 - (nav / rollmax)
    return float(dd.max())

def downside_deviation(rets: pd.Series) -> float:
    neg = rets[rets < 0]
    return float(neg.std(ddof=1) if len(neg) else 0.0)

def twr_from_returns(returns: List[float]) -> float:
    if not returns: return 0.0
    return prod((1 + r) for r in returns) - 1

def slope_log(series: pd.Series) -> float:
    """pendenza della retta su log(series) ~ t (OLS)"""
    y = np.log(series.replace(0, np.nan)).dropna()
    if len(y) < 3:
        return 0.0
    x = np.arange(len(y), dtype=float)
    b = np.polyfit(x[-len(y):], y.values, 1)[0]
    return float(b)

def realized_r(nav: pd.Series, win: int) -> float:
    if len(nav) <= win: return 0.0
    return float(nav.iloc[-1] / nav.iloc[-1-win] - 1.0)


# ---------- Wrapper principale ----------
@dataclass
class SignalResult:
    regime: str                 # UP / FLAT / DOWN
    enter: bool                 # trigger ingresso
    exit: bool                  # trigger uscita
    score: float                # score sintetico
    info: Dict                  # indicatori per logging


def compute_signals(
    price_series: pd.Series,          # serie prezzo/NAV (index datetime)
    tvl_series: pd.Series = None,     # opzionale (coerente come index)
    apy_series: pd.Series = None,     # opzionale (stima real/teorica)
    loop_minutes: int = 5,
    apy_min: float = 0.06,            # 6% minimo annuo
    gap_tau: float = 0.10,            # tolleranza gap APY-realizzato
    prev_state: Dict = None           # stato precedente per isteresi
) -> Tuple[SignalResult, LoopProfile]:

    prof = _choose_profile(loop_minutes)

    # 1) Resample coerente
    px = price_series.sort_index().resample(prof.resample_rule).last().dropna()

    # 2) Indicatori base
    ema_fast = ema(px, prof.ema_fast_bars)
    ema_slow = ema(px, prof.ema_slow_bars)
    macd_like = ema_fast - ema_slow
    slope = slope_log(ema_slow.tail(prof.ema_slow_bars))
    rets_log = log_returns(px).dropna()
    dd_local = max_drawdown(px.tail(prof.ema_slow_bars))
    vol_down = downside_deviation(rets_log.tail(prof.ema_slow_bars))

    # 3) Rendimento realizzato (coerente con finestra)
    r1 = realized_r(px, 1)
    r7 = realized_r(px, min(7 * max(1, 5 // prof.loop_minutes), 7))  # robust
    r30 = realized_r(px, max(2, int(30 * 24 * 60 / max(60, prof.loop_minutes)) // (60//(prof.loop_minutes if prof.loop_minutes<60 else 60))))
    # fallback più semplice se il calcolo sopra risultasse troppo aggressivo:
    if r30 == 0.0:
        r30 = realized_r(px, min(len(px)-1, prof.ema_slow_bars))

    # 4) ΔTVL / ΔAPY coerenti (se forniti)
    dTVL7 = 0.0
    if tvl_series is not None and len(tvl_series) > 8:
        tvl = tvl_series.sort_index().resample(prof.resample_rule).last().dropna()
        dTVL7 = float((tvl.iloc[-1] - tvl.iloc[-8]) / max(1e-9, tvl.iloc[-8]))

    dAPY = 0.0
    apy_gap = 0.0
    if apy_series is not None and len(apy_series) > 8:
        apy = apy_series.sort_index().resample(prof.resample_rule).last().dropna()
        dAPY = float((apy.iloc[-1] - apy.iloc[-8]) / max(1e-9, apy.iloc[-8]))
        # annualizzazione "realizzata" approssimata da r7:
        real_ann = (1 + (r7 / max(1, 7)))**365 - 1 if r7 else 0.0
        apy_gap = max(0.0, float(apy.iloc[-1]) - real_ann - gap_tau)

    # 5) Classificazione di regime
    eps = 5e-4
    if r7 < 0 or slope < 0 or dd_local > prof.dd_stop or dTVL7 < -0.10:
        regime = "DOWN"
    elif abs(r7) <= eps or abs(slope) <= eps:
        regime = "FLAT"
    else:
        regime = "UP"

    # 6) Score sintetico (pesi leggeri)
    w = dict(w1=3, w2=2, w3=2, w4=1.5, w5=2, w6=1, w7=0.5, w8=1)
    score = (w['w1']*r7 + w['w2']*r30 + w['w3']*slope
             - w['w4']*vol_down - w['w5']*dd_local - w['w6']*apy_gap
             + w['w7']*min(0.0, dAPY) + w['w8']*dTVL7)
    if regime == "DOWN":
        score = min(score, 0.0)

    # 7) Isteresi (enter/exit) + vincolo APY
    apy_ok = True if apy_series is None else (float(apy.resample(prof.resample_rule).last().iloc[-1]) >= apy_min)
    thresh_in, thresh_hold, thresh_out = 0.8, 0.3, 0.0

    # memoria corta per conferma barre
    prev = prev_state or {}
    in_count  = int(prev.get("in_count", 0))
    out_count = int(prev.get("out_count", 0))
    holding   = bool(prev.get("holding", False))

    enter_sig = (regime == "UP" and score > thresh_in and apy_ok and vol_down <= prof.vol_cap)
    exit_sig  = (regime == "DOWN" or score < thresh_out or dd_local > prof.dd_stop or not apy_ok)

    # applica conferme
    if enter_sig:
        in_count += 1
    else:
        in_count = 0
    if exit_sig:
        out_count += 1
    else:
        out_count = 0

    do_enter = (in_count >= prof.confirm_bars_in)
    do_exit  = (out_count >= prof.confirm_bars_out)

    # stato holding
    if holding:
        if do_exit:
            holding = False
            out_count = 0
    else:
        if do_enter:
            holding = True
            in_count = 0

    info = dict(
        ema_fast=float(ema_fast.iloc[-1]),
        ema_slow=float(ema_slow.iloc[-1]),
        macd=float(macd_like.iloc[-1]),
        slope=slope, r1=r1, r7=r7, r30=r30,
        dd=dd_local, vol_down=vol_down,
        dTVL7=dTVL7, dAPY=dAPY, apy_gap=apy_gap,
        apy_min=apy_min, apy_ok=apy_ok,
        confirm_in=in_count, confirm_out=out_count,
        holding=holding
    )

    return SignalResult(regime=regime, enter=do_enter, exit=do_exit, score=score, info=info), prof
