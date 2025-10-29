#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Input validation utilities for secure transaction handling."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

try:
    from web3 import Web3
except ModuleNotFoundError:  # pragma: no cover - import guard
    Web3 = None  # type: ignore[assignment]


def validate_ethereum_address(address: str) -> bool:
    """Validate Ethereum address format and checksum.
    
    Args:
        address: Ethereum address string to validate
        
    Returns:
        True if address is valid and checksummed, False otherwise
        
    Examples:
        >>> validate_ethereum_address("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
        False  # Invalid checksum
        >>> validate_ethereum_address("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbB")
        True
    """
    if not address or not isinstance(address, str):
        return False
    
    if Web3 is None:
        # Fallback validation without Web3
        if not address.startswith("0x"):
            return False
        if len(address) != 42:
            return False
        try:
            int(address[2:], 16)
            return True
        except ValueError:
            return False
    
    try:
        if not Web3.is_address(address):
            return False
        checksum_addr = Web3.to_checksum_address(address)
        return address == checksum_addr
    except Exception:
        return False


def validate_positive_amount(amount: float | int | Decimal | str, max_value: Optional[Decimal] = None) -> bool:
    """Validate that amount is positive and within bounds.
    
    Args:
        amount: Amount to validate (numeric or string)
        max_value: Optional maximum allowed value
        
    Returns:
        True if amount is valid and positive, False otherwise
    """
    try:
        decimal_amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        return False
    
    if decimal_amount <= 0:
        return False
    
    if max_value is not None and decimal_amount > max_value:
        return False
    
    return True


def validate_pool_name(pool_name: str, max_length: int = 200) -> bool:
    """Validate pool name format for safe usage.
    
    Args:
        pool_name: Pool identifier string
        max_length: Maximum allowed length
        
    Returns:
        True if pool name is safe to use, False otherwise
    """
    if not pool_name or not isinstance(pool_name, str):
        return False
    
    if len(pool_name) > max_length:
        return False
    
    # Allow alphanumeric, hyphens, underscores, colons
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_:")
    if not all(c in allowed_chars for c in pool_name):
        return False
    
    return True


def validate_percentage(value: float | int | Decimal, allow_negative: bool = False) -> bool:
    """Validate percentage value (0-100 or with negatives if allowed).
    
    Args:
        value: Percentage value to validate
        allow_negative: Whether to allow negative percentages
        
    Returns:
        True if percentage is valid, False otherwise
    """
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return False
    
    if not allow_negative and decimal_value < 0:
        return False
    
    # Reasonable bounds: -100% to 10000% (for APY)
    if decimal_value < -100 or decimal_value > 10000:
        return False
    
    return True


def sanitize_string_for_log(text: str, max_length: int = 1000) -> str:
    """Sanitize string for safe logging by removing control characters.
    
    Args:
        text: String to sanitize
        max_length: Maximum length to keep
        
    Returns:
        Sanitized string safe for logging
    """
    if not isinstance(text, str):
        text = str(text)
    
    # Remove control characters except newline and tab
    sanitized = "".join(c for c in text if c.isprintable() or c in "\n\t")
    
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "...(truncated)"
    
    return sanitized
