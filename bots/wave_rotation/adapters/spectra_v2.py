#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Placeholder adapter for Spectra v2 (formerly APWine).

Spectra v2 is a yield tokenization protocol.
"""

from __future__ import annotations

from typing import Dict

from .base import Adapter


class SpectraV2Adapter(Adapter):
    """
    Placeholder for Spectra v2 adapter.
    
    Required configuration:
    - principal_token: Principal token address
    - yield_token: Yield token address
    """

    def __init__(self, w3, config: Dict[str, object], signer, sender: str):
        raise NotImplementedError(
            "Spectra v2 adapter requires implementation. "
            "See Spectra documentation for yield tokenization mechanics."
        )

    def deposit_all(self) -> Dict[str, object]:
        return {
            "status": "not_implemented",
            "reason": "Spectra v2 requires specialized implementation",
        }

    def withdraw_all(self) -> Dict[str, object]:
        return {
            "status": "not_implemented",
            "reason": "Spectra v2 requires specialized implementation",
        }
