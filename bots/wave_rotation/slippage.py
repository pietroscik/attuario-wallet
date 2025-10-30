#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Slippage protection utilities for swaps and deposits."""

from __future__ import annotations

import os
from decimal import Decimal, ROUND_DOWN
from typing import Optional, Union


def get_slippage_bps() -> int:
    """
    Get slippage tolerance in basis points from environment.
    
    Returns:
        Slippage in basis points (default: 100 = 1%)
    """
    raw = os.getenv("SLIPPAGE_BPS", "100")
    try:
        bps = int(raw)
        return max(1, min(bps, 10000))  # Clamp to 0.01% - 100%
    except ValueError:
        return 100


def calculate_min_amount_out(
    expected_amount: Union[int, float, Decimal],
    slippage_bps: Optional[int] = None,
) -> int:
    """
    Calculate minimum amount out with slippage protection.
    
    Args:
        expected_amount: Expected amount to receive
        slippage_bps: Slippage tolerance in basis points (default from env)
        
    Returns:
        Minimum amount out (integer)
    """
    if slippage_bps is None:
        slippage_bps = get_slippage_bps()
    
    # Convert to Decimal for precision
    if isinstance(expected_amount, (int, float)):
        amount_dec = Decimal(str(expected_amount))
    else:
        amount_dec = Decimal(expected_amount)
    
    # Calculate minimum: amount * (1 - slippage)
    slippage_factor = Decimal(10000 - slippage_bps) / Decimal(10000)
    min_amount = amount_dec * slippage_factor
    
    # Round down to be conservative
    return int(min_amount.quantize(Decimal(1), rounding=ROUND_DOWN))


def validate_slippage(
    expected_amount: Union[int, float],
    actual_amount: Union[int, float],
    slippage_bps: Optional[int] = None,
) -> bool:
    """
    Validate that actual amount is within acceptable slippage.
    
    Args:
        expected_amount: Expected amount
        actual_amount: Actual amount received
        slippage_bps: Slippage tolerance in basis points
        
    Returns:
        True if within tolerance, False otherwise
    """
    if slippage_bps is None:
        slippage_bps = get_slippage_bps()
    
    min_amount = calculate_min_amount_out(expected_amount, slippage_bps)
    return actual_amount >= min_amount


def get_price_impact_bps(
    amount_in: Union[int, float],
    amount_out: Union[int, float],
    expected_rate: Union[int, float],
) -> int:
    """
    Calculate price impact in basis points.
    
    Args:
        amount_in: Input amount
        amount_out: Output amount
        expected_rate: Expected exchange rate (out per in)
        
    Returns:
        Price impact in basis points (positive = worse than expected)
    """
    if amount_in <= 0 or expected_rate <= 0:
        return 0
    
    expected_out = Decimal(str(amount_in)) * Decimal(str(expected_rate))
    actual_out = Decimal(str(amount_out))
    
    if expected_out == 0:
        return 0
    
    # Impact = (expected - actual) / expected * 10000
    impact = ((expected_out - actual_out) / expected_out) * Decimal(10000)
    
    return int(impact)


class SlippageConfig:
    """Configuration for slippage protection."""
    
    def __init__(
        self,
        slippage_bps: Optional[int] = None,
        max_price_impact_bps: Optional[int] = None,
        min_output_ratio: Optional[float] = None,
    ):
        """
        Initialize slippage configuration.
        
        Args:
            slippage_bps: Slippage tolerance in basis points
            max_price_impact_bps: Maximum acceptable price impact
            min_output_ratio: Minimum output ratio (e.g., 0.99 = 99% of expected)
        """
        self.slippage_bps = slippage_bps or get_slippage_bps()
        self.max_price_impact_bps = max_price_impact_bps or int(
            os.getenv("MAX_PRICE_IMPACT_BPS", "500")  # 5% default
        )
        self.min_output_ratio = min_output_ratio or float(
            os.getenv("MIN_OUTPUT_RATIO", "0.95")  # 95% default
        )
    
    def calculate_min_out(self, expected: Union[int, float]) -> int:
        """Calculate minimum output amount."""
        return calculate_min_amount_out(expected, self.slippage_bps)
    
    def validate_output(
        self,
        expected: Union[int, float],
        actual: Union[int, float],
    ) -> tuple[bool, str]:
        """
        Validate output amount.
        
        Returns:
            Tuple of (is_valid, reason)
        """
        min_out = self.calculate_min_out(expected)
        
        if actual < min_out:
            return False, f"Output {actual} below minimum {min_out} (slippage)"
        
        ratio = float(actual) / float(expected) if expected > 0 else 0.0
        if ratio < self.min_output_ratio:
            return False, f"Output ratio {ratio:.2%} below minimum {self.min_output_ratio:.2%}"
        
        return True, "ok"
    
    def validate_price_impact(
        self,
        amount_in: Union[int, float],
        amount_out: Union[int, float],
        expected_rate: Union[int, float],
    ) -> tuple[bool, str]:
        """
        Validate price impact.
        
        Returns:
            Tuple of (is_valid, reason)
        """
        impact_bps = get_price_impact_bps(amount_in, amount_out, expected_rate)
        
        if impact_bps > self.max_price_impact_bps:
            return False, f"Price impact {impact_bps}bps exceeds max {self.max_price_impact_bps}bps"
        
        return True, f"impact={impact_bps}bps"


def create_slippage_config() -> SlippageConfig:
    """Create slippage configuration from environment."""
    return SlippageConfig()
