#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Placeholder adapter for Etherex CL (Concentrated Liquidity) on Linea.

Etherex CL is similar to Uniswap v3 style concentrated liquidity.
"""

from __future__ import annotations

from typing import Dict

from .base import Adapter


class EtherexCLAdapter(Adapter):
    """
    Placeholder for Etherex CL adapter.
    
    Required configuration:
    - nft_manager: NFT position manager address
    - token0: First token address
    - token1: Second token address
    """

    def __init__(self, w3, config: Dict[str, object], signer, sender: str):
        raise NotImplementedError(
            "Etherex CL adapter requires implementation on Linea chain. "
            "Similar to Uniswap v3 concentrated liquidity mechanics."
        )

    def deposit_all(self) -> Dict[str, object]:
        return {
            "status": "not_implemented",
            "reason": "Etherex CL requires Linea-specific implementation",
        }

    def withdraw_all(self) -> Dict[str, object]:
        return {
            "status": "not_implemented",
            "reason": "Etherex CL requires Linea-specific implementation",
        }
