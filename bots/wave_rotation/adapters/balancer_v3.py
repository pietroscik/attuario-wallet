#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Placeholder adapter for Balancer v3 pools.

Balancer v3 introduces new pool types and liquidity management.
"""

from __future__ import annotations

from typing import Dict

from .base import Adapter


class BalancerV3Adapter(Adapter):
    """
    Placeholder for Balancer v3 adapter.
    
    Required configuration:
    - vault: Balancer v3 vault address
    - pool_id: Pool ID within the vault
    - tokens: List of token addresses in the pool
    """

    def __init__(self, w3, config: Dict[str, object], signer, sender: str):
        raise NotImplementedError(
            "Balancer v3 adapter requires implementation. "
            "See Balancer v3 documentation for vault and pool interaction patterns."
        )

    def deposit_all(self) -> Dict[str, object]:
        return {
            "status": "not_implemented",
            "reason": "Balancer v3 requires specialized implementation",
        }

    def withdraw_all(self) -> Dict[str, object]:
        return {
            "status": "not_implemented",
            "reason": "Balancer v3 requires specialized implementation",
        }
