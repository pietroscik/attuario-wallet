#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Safe decimal and amount handling utilities to prevent truncation and overflow."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Optional, Union

try:
    from web3 import Web3
except ModuleNotFoundError:
    Web3 = None  # type: ignore[assignment]


def safe_decimals(value: int, default: int = 18) -> int:
    """
    Safely handle token decimals value.
    
    Args:
        value: Decimals value from contract
        default: Default decimals if value is invalid
        
    Returns:
        Valid decimals value (0-77)
    """
    if not isinstance(value, int):
        return default
    
    # ERC-20 decimals typically 0-18, but support up to 77 (max for uint8)
    if value < 0:
        return default
    if value > 77:
        return default
    
    return value


def safe_amount(
    amount: Union[int, float, Decimal, str],
    decimals: int = 18,
    max_value: Optional[Union[int, float, Decimal]] = None,
) -> int:
    """
    Convert amount to safe integer representation for contract calls.
    
    Args:
        amount: Amount in human-readable units (e.g., 1.5 ETH)
        decimals: Token decimals
        max_value: Optional maximum value (e.g., balanceOf result)
        
    Returns:
        Integer amount in smallest units (e.g., wei)
    """
    try:
        # Convert to Decimal for precision
        if isinstance(amount, str):
            dec_amount = Decimal(amount)
        elif isinstance(amount, (int, float)):
            dec_amount = Decimal(str(amount))
        elif isinstance(amount, Decimal):
            dec_amount = amount
        else:
            raise ValueError(f"Unsupported amount type: {type(amount)}")
        
        # Check for negative
        if dec_amount < 0:
            return 0
        
        # Scale to smallest units
        multiplier = Decimal(10 ** decimals)
        scaled = dec_amount * multiplier
        
        # Round down to avoid exceeding balance
        int_amount = int(scaled.quantize(Decimal(1), rounding=ROUND_DOWN))
        
        # Clamp to max_value if provided
        if max_value is not None:
            if isinstance(max_value, (float, str, Decimal)):
                max_int = int(Decimal(str(max_value)))
            else:
                max_int = int(max_value)
            
            int_amount = min(int_amount, max_int)
        
        return max(0, int_amount)
    
    except (InvalidOperation, ValueError, OverflowError):
        return 0


def clamp_to_balance(
    amount: Union[int, float, Decimal],
    balance: int,
    decimals: int = 18,
) -> int:
    """
    Clamp amount to available balance.
    
    Args:
        amount: Desired amount (human-readable or wei)
        balance: Available balance in wei
        decimals: Token decimals
        
    Returns:
        Clamped amount in wei
    """
    if balance <= 0:
        return 0
    
    # If amount is already in wei (large integer), clamp directly
    if isinstance(amount, int) and amount > 10**decimals:
        return min(amount, balance)
    
    # Otherwise convert and clamp
    amount_wei = safe_amount(amount, decimals)
    return min(amount_wei, balance)


def format_amount(
    amount_wei: int,
    decimals: int = 18,
    precision: int = 6,
) -> str:
    """
    Format wei amount as human-readable string.
    
    Args:
        amount_wei: Amount in smallest units
        decimals: Token decimals
        precision: Decimal places to display
        
    Returns:
        Formatted string
    """
    if Web3 is not None:
        # Use Web3's utility if available
        try:
            eth_amount = Web3.from_wei(amount_wei, 'ether')
            return f"{eth_amount:.{precision}f}"
        except Exception:
            pass
    
    # Fallback: manual conversion
    divisor = Decimal(10 ** decimals)
    amount_dec = Decimal(amount_wei) / divisor
    
    # Format with specified precision
    format_str = f"{{:.{precision}f}}"
    return format_str.format(float(amount_dec))


def is_fee_on_transfer_token(
    token_address: str,
    amount_to_test: int = 1000000,
    w3 = None,
    sender: Optional[str] = None,
) -> bool:
    """
    Detect if token has fee-on-transfer mechanism.
    
    This is a heuristic check - not foolproof but catches common cases.
    
    Args:
        token_address: Token contract address
        amount_to_test: Amount to simulate for testing
        w3: Web3 instance
        sender: Sender address for simulation
        
    Returns:
        True if token appears to have fee-on-transfer
    """
    # Note: This is a placeholder for future implementation
    # Actual implementation would require:
    # 1. Call transfer() in a simulation
    # 2. Check if received amount < sent amount
    # 3. Handle various fee-on-transfer patterns
    
    # For now, maintain a known list
    known_fot_tokens = {
        # Add known fee-on-transfer tokens here
        # Example: "0x..." (token address lowercase)
    }
    
    return token_address.lower() in known_fot_tokens


def safe_percentage(
    numerator: Union[int, float, Decimal],
    denominator: Union[int, float, Decimal],
    default: float = 0.0,
) -> float:
    """
    Safely calculate percentage avoiding division by zero.
    
    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Default value if calculation fails
        
    Returns:
        Percentage as float
    """
    try:
        num = Decimal(str(numerator))
        denom = Decimal(str(denominator))
        
        if denom == 0:
            return default
        
        return float(num / denom)
    except (InvalidOperation, ValueError, ZeroDivisionError):
        return default
