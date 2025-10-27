#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Operational guardrails (gas ceiling, economic edge checks)."""

from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from typing import Tuple

from web3 import Web3


def _decimal_env(name: str, default: str) -> Decimal:
    raw = os.getenv(name, default)
    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError):
        return Decimal(default)


def gas_ceiling_ok(w3: Web3) -> Tuple[bool, str]:
    """Check that current gas price is below configured ceiling (if any)."""

    ceiling_gwei_raw = os.getenv("GAS_PRICE_MAX_GWEI")
    if not ceiling_gwei_raw:
        return True, "gas:unchecked"

    try:
        ceiling_gwei = float(ceiling_gwei_raw)
    except ValueError:
        return True, "gas:invalid_ceiling"

    if ceiling_gwei <= 0:
        return True, "gas:disabled_ceiling"

    gas_price_wei = w3.eth.gas_price
    gas_price_gwei = gas_price_wei / 1e9
    if gas_price_gwei > ceiling_gwei:
        return False, f"gas>{ceiling_gwei:g}gwei({gas_price_gwei:.2f})"
    return True, f"gas_ok:{gas_price_gwei:.2f}gwei"


def should_move(
    capital_eth: float,
    score_best: float,
    score_current: float | None,
    *,
    est_move_gas: int,
    w3: Web3,
) -> Tuple[bool, str]:
    """Economic guardrail disattivato: consente sempre il movimento."""

    return True, "edge_disabled"
