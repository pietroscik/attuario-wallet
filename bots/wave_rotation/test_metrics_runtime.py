#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for metrics_runtime module - adaptive asset selection criteria
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from metrics_runtime import (
    _choose_profile,
    LoopProfile,
    ema,
    log_returns,
    max_drawdown,
    downside_deviation,
    twr_from_returns,
    slope_log,
    realized_r,
    compute_signals,
    SignalResult,
)


def test_choose_profile_5min():
    """Test profile selection for 5 minute loop"""
    prof = _choose_profile(5)
    assert prof.loop_minutes == 5
    assert prof.resample_rule == "5min"
    assert prof.ema_fast_bars == 12
    assert prof.ema_slow_bars == 36
    assert prof.confirm_bars_in == 2
    assert prof.confirm_bars_out == 1
    assert prof.dd_stop == 0.15
    assert prof.vol_cap == 0.025


def test_choose_profile_15min():
    """Test profile selection for 15 minute loop"""
    prof = _choose_profile(15)
    assert prof.loop_minutes == 15
    assert prof.resample_rule == "15min"
    assert prof.ema_fast_bars == 12
    assert prof.ema_slow_bars == 48


def test_choose_profile_60min():
    """Test profile selection for 60 minute loop"""
    prof = _choose_profile(60)
    assert prof.loop_minutes == 60
    assert prof.resample_rule == "60min"
    assert prof.ema_fast_bars == 24
    assert prof.ema_slow_bars == 96


def test_choose_profile_daily():
    """Test profile selection for daily loop"""
    prof = _choose_profile(1440)
    assert prof.loop_minutes == 1440
    assert prof.resample_rule == "1D"
    assert prof.ema_fast_bars == 7
    assert prof.ema_slow_bars == 30


def test_ema_calculation():
    """Test EMA calculation"""
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = ema(series, 3)
    assert len(result) == len(series)
    assert result.iloc[-1] > result.iloc[0]  # Should be increasing


def test_log_returns():
    """Test log returns calculation"""
    series = pd.Series([100.0, 110.0, 121.0, 133.1])
    result = log_returns(series)
    assert len(result) == len(series)
    assert pd.isna(result.iloc[0])  # First value should be NaN
    assert result.iloc[1] > 0  # Should be positive for increasing series


def test_max_drawdown():
    """Test max drawdown calculation"""
    # Series with a drawdown
    series = pd.Series([100.0, 110.0, 90.0, 95.0, 120.0])
    dd = max_drawdown(series)
    assert dd > 0  # Should have positive drawdown
    assert dd <= 1.0  # Should not exceed 100%


def test_downside_deviation():
    """Test downside deviation calculation"""
    # Series with mixed returns
    returns = pd.Series([0.05, -0.03, 0.02, -0.04, 0.01, -0.02])
    vol = downside_deviation(returns)
    assert vol >= 0  # Should be non-negative


def test_twr_from_returns():
    """Test TWR calculation"""
    returns = [0.10, 0.05, -0.03, 0.08]
    twr = twr_from_returns(returns)
    assert twr > 0  # Should be positive for net positive returns


def test_slope_log():
    """Test slope calculation"""
    # Increasing series
    series = pd.Series([100.0, 105.0, 110.0, 115.0, 120.0])
    slope = slope_log(series)
    assert slope > 0  # Should be positive for increasing series


def test_realized_r():
    """Test realized return calculation"""
    series = pd.Series([100.0, 105.0, 110.0, 115.0])
    r = realized_r(series, 2)
    assert r > 0  # Should be positive for increasing series


def create_mock_price_series(start_price=100.0, days=100, trend=0.001, volatility=0.02):
    """Create a mock price series for testing"""
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days, freq='D')
    prices = [start_price]
    for i in range(1, days):
        # Random walk with drift
        change = trend + np.random.normal(0, volatility)
        prices.append(prices[-1] * (1 + change))
    return pd.Series(prices, index=dates)


def test_compute_signals_up_regime():
    """Test signal computation for UP regime"""
    # Create uptrending price series
    price_series = create_mock_price_series(start_price=100.0, days=100, trend=0.01, volatility=0.005)
    
    sig, prof = compute_signals(
        price_series=price_series,
        loop_minutes=5,
        apy_min=0.06,
        gap_tau=0.10,
    )
    
    assert isinstance(sig, SignalResult)
    assert isinstance(prof, LoopProfile)
    assert sig.regime in ["UP", "FLAT", "DOWN"]
    assert isinstance(sig.enter, bool)
    assert isinstance(sig.exit, bool)
    assert isinstance(sig.score, float)
    assert isinstance(sig.info, dict)


def test_compute_signals_down_regime():
    """Test signal computation for DOWN regime"""
    # Create downtrending price series
    price_series = create_mock_price_series(start_price=100.0, days=100, trend=-0.01, volatility=0.005)
    
    sig, prof = compute_signals(
        price_series=price_series,
        loop_minutes=5,
        apy_min=0.06,
        gap_tau=0.10,
    )
    
    assert isinstance(sig, SignalResult)
    assert sig.regime in ["UP", "FLAT", "DOWN"]


def test_compute_signals_with_tvl_and_apy():
    """Test signal computation with TVL and APY series"""
    price_series = create_mock_price_series(start_price=100.0, days=100, trend=0.005, volatility=0.01)
    tvl_series = create_mock_price_series(start_price=1000000.0, days=100, trend=0.002, volatility=0.05)
    apy_series = pd.Series([0.08] * 100, index=price_series.index)
    
    sig, prof = compute_signals(
        price_series=price_series,
        tvl_series=tvl_series,
        apy_series=apy_series,
        loop_minutes=15,
        apy_min=0.06,
        gap_tau=0.10,
    )
    
    assert isinstance(sig, SignalResult)
    assert 'dTVL7' in sig.info
    assert 'dAPY' in sig.info
    assert 'apy_gap' in sig.info


def test_compute_signals_hysteresis():
    """Test hysteresis with state preservation"""
    price_series = create_mock_price_series(start_price=100.0, days=100, trend=0.005, volatility=0.01)
    
    # First call - no previous state
    sig1, prof1 = compute_signals(
        price_series=price_series,
        loop_minutes=5,
        apy_min=0.06,
        prev_state=None,
    )
    
    # Second call - with previous state
    prev_state = {
        "holding": sig1.info["holding"],
        "in_count": sig1.info["confirm_in"],
        "out_count": sig1.info["confirm_out"],
    }
    
    sig2, prof2 = compute_signals(
        price_series=price_series,
        loop_minutes=5,
        apy_min=0.06,
        prev_state=prev_state,
    )
    
    assert isinstance(sig2, SignalResult)
    assert 'holding' in sig2.info
    assert 'confirm_in' in sig2.info
    assert 'confirm_out' in sig2.info


def test_signal_info_structure():
    """Test that signal info contains all expected fields"""
    price_series = create_mock_price_series(start_price=100.0, days=100, trend=0.005, volatility=0.01)
    
    sig, prof = compute_signals(
        price_series=price_series,
        loop_minutes=5,
    )
    
    expected_fields = [
        'ema_fast', 'ema_slow', 'macd', 'slope',
        'r1', 'r7', 'r30', 'dd', 'vol_down',
        'dTVL7', 'dAPY', 'apy_gap', 'apy_min', 'apy_ok',
        'confirm_in', 'confirm_out', 'holding'
    ]
    
    for field in expected_fields:
        assert field in sig.info, f"Missing field: {field}"


if __name__ == "__main__":
    # Run basic tests
    test_choose_profile_5min()
    test_choose_profile_15min()
    test_choose_profile_60min()
    test_choose_profile_daily()
    test_ema_calculation()
    test_log_returns()
    test_max_drawdown()
    test_downside_deviation()
    test_twr_from_returns()
    test_slope_log()
    test_realized_r()
    test_compute_signals_up_regime()
    test_compute_signals_down_regime()
    test_compute_signals_with_tvl_and_apy()
    test_compute_signals_hysteresis()
    test_signal_info_structure()
    
    print("✅ All metrics_runtime tests passed!")
