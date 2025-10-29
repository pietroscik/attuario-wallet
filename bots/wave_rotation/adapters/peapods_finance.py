#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Placeholder adapter for Peapods Finance on Sonic chain.

Peapods Finance provides lending/borrowing on Sonic.
"""

from __future__ import annotations

from typing import Dict

from .base import Adapter


class PeapodsFinanceAdapter(Adapter):
    """
    Placeholder for Peapods Finance adapter.
    
    Required configuration:
    - market: Peapods market address (on Sonic)
    - asset: Asset to deposit
    """

    def __init__(self, w3, config: Dict[str, object], signer, sender: str):
        raise NotImplementedError(
            "Peapods Finance adapter requires implementation for Sonic chain."
        )

    def deposit_all(self) -> Dict[str, object]:
        return {
            "status": "not_implemented",
            "reason": "Peapods Finance requires Sonic-specific implementation",
        }

    def withdraw_all(self) -> Dict[str, object]:
        return {
            "status": "not_implemented",
            "reason": "Peapods Finance requires Sonic-specific implementation",
        }
