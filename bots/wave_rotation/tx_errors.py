#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Transaction error classes and revert decoding for on-chain operations."""

from __future__ import annotations

from typing import Optional


class TransactionError(Exception):
    """Base class for transaction-related errors."""
    
    def __init__(self, message: str, tx_hash: Optional[str] = None):
        super().__init__(message)
        self.tx_hash = tx_hash


class NonceError(TransactionError):
    """Nonce-related errors (nonce too low, replacement underpriced, etc.)."""
    pass


class GasError(TransactionError):
    """Gas-related errors (insufficient funds, gas limit exceeded, etc.)."""
    pass


class RevertError(TransactionError):
    """Transaction reverted with a reason."""
    
    def __init__(self, message: str, reason: Optional[str] = None, tx_hash: Optional[str] = None):
        super().__init__(message, tx_hash)
        self.reason = reason


class SlippageError(RevertError):
    """Slippage protection triggered."""
    pass


class InsufficientLiquidityError(RevertError):
    """Insufficient liquidity in pool/protocol."""
    pass


class PausedError(TransactionError):
    """Protocol or vault is paused."""
    pass


class TimeoutError(TransactionError):
    """Transaction confirmation timeout."""
    pass


def decode_revert_reason(error_data: str) -> Optional[str]:
    """
    Decode revert reason from error data.
    
    Args:
        error_data: Hex-encoded error data from transaction receipt
        
    Returns:
        Decoded revert reason string or None
    """
    if not error_data or not isinstance(error_data, str):
        return None
        
    # Remove 0x prefix
    data = error_data[2:] if error_data.startswith("0x") else error_data
    
    # Standard Error(string) selector: 0x08c379a0
    if data.startswith("08c379a0"):
        try:
            # Skip selector (4 bytes = 8 hex chars), decode ABI-encoded string
            # Offset (32 bytes), length (32 bytes), then UTF-8 string
            offset_start = 8
            length_start = offset_start + 64
            length_end = length_start + 64
            
            if len(data) > length_end:
                length_hex = data[length_start:length_end]
                length = int(length_hex, 16)
                
                string_start = length_end
                string_end = string_start + (length * 2)
                
                if len(data) >= string_end:
                    string_hex = data[string_start:string_end]
                    reason_bytes = bytes.fromhex(string_hex)
                    return reason_bytes.decode('utf-8', errors='ignore')
        except Exception:
            pass
    
    # Panic(uint256) selector: 0x4e487b71
    elif data.startswith("4e487b71"):
        try:
            panic_code_hex = data[8:72]  # Skip selector, get 32-byte code
            panic_code = int(panic_code_hex, 16)
            panic_reasons = {
                0x00: "Generic panic",
                0x01: "Assertion failed",
                0x11: "Arithmetic overflow/underflow",
                0x12: "Division by zero",
                0x21: "Invalid enum value",
                0x22: "Invalid storage access",
                0x31: "Pop from empty array",
                0x32: "Array index out of bounds",
                0x41: "Out of memory",
                0x51: "Invalid internal function",
            }
            return panic_reasons.get(panic_code, f"Panic code: 0x{panic_code:02x}")
        except Exception:
            pass
    
    return None


def classify_error(error_message: str, error_data: Optional[str] = None) -> TransactionError:
    """
    Classify transaction error based on message and data.
    
    Args:
        error_message: Error message from exception
        error_data: Optional error data for revert decoding
        
    Returns:
        Classified TransactionError subclass
    """
    message_lower = error_message.lower()
    
    # Nonce errors
    if any(phrase in message_lower for phrase in [
        "nonce too low",
        "nonce has already been used",
        "replacement transaction underpriced",
    ]):
        return NonceError(error_message)
    
    # Gas errors
    if any(phrase in message_lower for phrase in [
        "insufficient funds",
        "gas required exceeds allowance",
        "intrinsic gas too low",
        "max fee per gas less than block base fee",
    ]):
        return GasError(error_message)
    
    # Paused errors
    if any(phrase in message_lower for phrase in [
        "paused",
        "shutdown",
        "emergency",
    ]):
        return PausedError(error_message)
    
    # Slippage errors
    if any(phrase in message_lower for phrase in [
        "slippage",
        "price impact",
        "min amount",
        "insufficient output",
    ]):
        reason = decode_revert_reason(error_data) if error_data else None
        return SlippageError(error_message, reason=reason)
    
    # Liquidity errors
    if any(phrase in message_lower for phrase in [
        "insufficient liquidity",
        "insufficient reserves",
        "k",  # Uniswap K invariant
    ]):
        reason = decode_revert_reason(error_data) if error_data else None
        return InsufficientLiquidityError(error_message, reason=reason)
    
    # Generic revert
    if "revert" in message_lower or "execution reverted" in message_lower:
        reason = decode_revert_reason(error_data) if error_data else None
        return RevertError(error_message, reason=reason)
    
    # Timeout
    if "timeout" in message_lower:
        return TimeoutError(error_message)
    
    # Unclassified
    return TransactionError(error_message)
