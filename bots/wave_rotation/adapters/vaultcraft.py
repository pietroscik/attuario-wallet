#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Placeholder adapter for Vaultcraft vaults.

Vaultcraft provides yield optimization vaults on Arbitrum.
"""

from __future__ import annotations

from typing import Dict

from .base import Adapter


class VaultcraftAdapter(Adapter):
    """
    Placeholder for Vaultcraft adapter.
    
    Vaultcraft vaults may follow ERC-4626 standard or have custom interfaces.
    
    Required configuration:
    - vault: Vaultcraft vault address
    - asset: Underlying asset address
    """

    def __init__(self, w3, config: Dict[str, object], signer, sender: str):
        raise NotImplementedError(
            "Vaultcraft adapter requires implementation. "
            "Check if vault follows ERC-4626 standard or requires custom logic."
        )

    def deposit_all(self) -> Dict[str, object]:
        return {
            "status": "not_implemented",
            "reason": "Vaultcraft requires specialized implementation",
        }

    def withdraw_all(self) -> Dict[str, object]:
        return {
            "status": "not_implemented",
            "reason": "Vaultcraft requires specialized implementation",
        }
