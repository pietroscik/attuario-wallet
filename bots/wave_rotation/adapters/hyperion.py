#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Placeholder adapter for Hyperion (Aptos-based DEX).

NOTE: This adapter requires Aptos-specific libraries and cannot use Web3.py.
"""

from __future__ import annotations

from typing import Dict

from .base import Adapter


class HyperionAdapter(Adapter):
    """
    Placeholder adapter for Hyperion on Aptos chain.
    
    Required configuration:
    - aptos_rpc: Aptos RPC endpoint
    - pool_address: Hyperion pool address
    - token_a: Token A type
    - token_b: Token B type
    """

    def __init__(self, w3, config: Dict[str, object], signer, sender: str):
        raise NotImplementedError(
            "Hyperion adapter requires Aptos-specific implementation. "
            "Please install aptos-sdk and implement Aptos wallet integration."
        )

    def deposit_all(self) -> Dict[str, object]:
        return {
            "status": "not_implemented",
            "reason": "Hyperion requires Aptos-specific implementation",
        }

    def withdraw_all(self) -> Dict[str, object]:
        return {
            "status": "not_implemented",
            "reason": "Hyperion requires Aptos-specific implementation",
        }
