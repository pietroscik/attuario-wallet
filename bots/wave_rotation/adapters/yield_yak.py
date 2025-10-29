#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Placeholder adapter for Yield Yak aggregator (Avalanche).

Yield Yak is an auto-compounder on Avalanche.
"""

from __future__ import annotations

from typing import Dict

from .base import Adapter


class YieldYakAdapter(Adapter):
    """
    Placeholder for Yield Yak adapter.
    
    Required configuration:
    - vault: Yield Yak vault address (on Avalanche)
    - deposit_token: Token to deposit
    """

    def __init__(self, w3, config: Dict[str, object], signer, sender: str):
        raise NotImplementedError(
            "Yield Yak adapter requires implementation for Avalanche chain. "
            "Vaults may follow ERC-4626 or have custom interfaces."
        )

    def deposit_all(self) -> Dict[str, object]:
        return {
            "status": "not_implemented",
            "reason": "Yield Yak requires Avalanche-specific implementation",
        }

    def withdraw_all(self) -> Dict[str, object]:
        return {
            "status": "not_implemented",
            "reason": "Yield Yak requires Avalanche-specific implementation",
        }
