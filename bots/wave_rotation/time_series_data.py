#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Helper functions for collecting time series data for metrics_runtime.
Provides price, TVL, and APY series collection from various sources.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import pandas as pd

try:
    import requests
except ModuleNotFoundError:
    requests = None

from constants import DEFAULT_HTTP_TIMEOUT


def get_price_series_for_pool(
    pool_id: str,
    pool_data: Dict,
    lookback_days: int = 90
) -> pd.Series:
    """
    Get price/NAV series for a pool.
    
    Args:
        pool_id: Pool identifier
        pool_data: Pool metadata from data sources
        lookback_days: Number of days of historical data
    
    Returns:
        pandas Series with datetime index and price values
    """
    # For now, create a synthetic series based on APY
    # In production, this would fetch from:
    # - DeFiLlama historical API
    # - On-chain price oracle
    # - Vault share price history
    
    apy = float(pool_data.get("apy", 0.0))
    
    # Create synthetic price series
    # Start with base price and apply daily APY-based growth
    dates = pd.date_range(
        end=datetime.now(),
        periods=lookback_days,
        freq='D'
    )
    
    # Simulate price evolution based on APY
    daily_rate = (1 + apy) ** (1/365) - 1
    base_price = 100.0
    prices = []
    
    for i in range(lookback_days):
        # Simple deterministic price evolution (no noise added)
        price = base_price * ((1 + daily_rate) ** i)
        prices.append(price)
    
    return pd.Series(prices, index=dates)


def get_tvl_series_for_pool(
    pool_id: str,
    pool_data: Dict,
    lookback_days: int = 90
) -> pd.Series:
    """
    Get TVL series for a pool.
    
    Args:
        pool_id: Pool identifier
        pool_data: Pool metadata from data sources
        lookback_days: Number of days of historical data
    
    Returns:
        pandas Series with datetime index and TVL values
    """
    # For now, create a synthetic series based on current TVL
    # In production, this would fetch from:
    # - DeFiLlama historical TVL API
    # - On-chain vault balance history
    
    current_tvl = float(pool_data.get("tvl_usd", 0.0))
    
    dates = pd.date_range(
        end=datetime.now(),
        periods=lookback_days,
        freq='D'
    )
    
    # Create relatively stable TVL with small variations
    tvl_values = [current_tvl] * lookback_days
    
    return pd.Series(tvl_values, index=dates)


def get_apy_series_for_pool(
    pool_id: str,
    pool_data: Dict,
    lookback_days: int = 90
) -> pd.Series:
    """
    Get APY series for a pool.
    
    Args:
        pool_id: Pool identifier
        pool_data: Pool metadata from data sources
        lookback_days: Number of days of historical data
    
    Returns:
        pandas Series with datetime index and APY values
    """
    # For now, create a synthetic series based on current APY
    # In production, this would fetch from:
    # - DeFiLlama historical APY API
    # - Protocol-specific APY history
    
    current_apy = float(pool_data.get("apy", 0.0))
    
    dates = pd.date_range(
        end=datetime.now(),
        periods=lookback_days,
        freq='D'
    )
    
    # Create relatively stable APY series
    apy_values = [current_apy] * lookback_days
    
    return pd.Series(apy_values, index=dates)


def fetch_defillama_historical_apy(
    pool_address: str,
    chain: str,
    lookback_days: int = 90
) -> Optional[pd.Series]:
    """
    Fetch historical APY data from DeFiLlama.
    
    Args:
        pool_address: Pool contract address
        chain: Chain name
        lookback_days: Days of history to fetch
    
    Returns:
        pandas Series with datetime index and APY values, or None if unavailable
    """
    if requests is None:
        return None
    
    # DeFiLlama historical chart endpoint
    # https://yields.llama.fi/chart/{pool_id}
    try:
        base_url = os.getenv("DEFILLAMA_API", "https://yields.llama.fi")
        url = f"{base_url.rstrip('/')}/chart/{pool_address}"
        
        response = requests.get(url, timeout=DEFAULT_HTTP_TIMEOUT)
        if not response.ok:
            return None
        
        data = response.json()
        if not data or "data" not in data:
            return None
        
        # Parse the data into a Series
        dates = []
        apys = []
        
        for entry in data["data"]:
            if "timestamp" in entry and "apy" in entry:
                timestamp = datetime.fromtimestamp(entry["timestamp"])
                apy = float(entry["apy"]) / 100.0  # Convert from percentage
                dates.append(timestamp)
                apys.append(apy)
        
        if not dates:
            return None
        
        series = pd.Series(apys, index=pd.DatetimeIndex(dates))
        series = series.sort_index()
        
        # Filter to requested lookback period
        cutoff = datetime.now() - timedelta(days=lookback_days)
        series = series[series.index >= cutoff]
        
        return series if len(series) > 0 else None
        
    except Exception as exc:
        print(f"[data] Failed to fetch DeFiLlama historical APY: {exc}")
        return None


def collect_pool_time_series(
    pool_id: str,
    pool_data: Dict,
    lookback_days: int = 90
) -> Tuple[pd.Series, Optional[pd.Series], Optional[pd.Series]]:
    """
    Collect all time series data for a pool.
    
    Args:
        pool_id: Pool identifier
        pool_data: Pool metadata
        lookback_days: Days of historical data
    
    Returns:
        Tuple of (price_series, tvl_series, apy_series)
        tvl_series and apy_series may be None if unavailable
    """
    price_series = get_price_series_for_pool(pool_id, pool_data, lookback_days)
    
    # Try to fetch real TVL/APY data, fall back to synthetic
    tvl_series = get_tvl_series_for_pool(pool_id, pool_data, lookback_days)
    apy_series = get_apy_series_for_pool(pool_id, pool_data, lookback_days)
    
    # Attempt to fetch real historical APY from DeFiLlama
    pool_address = pool_data.get("address", "")
    chain = pool_data.get("chain", "")
    if pool_address and chain:
        real_apy = fetch_defillama_historical_apy(pool_address, chain, lookback_days)
        if real_apy is not None:
            apy_series = real_apy
    
    return price_series, tvl_series, apy_series
