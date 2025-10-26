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
    """Return whether the expected edge justifies moving capital."""

    score_current = score_current or 0.0

    fx_rate = _decimal_env("FX_EUR_PER_ETH", "3000")
    min_edge_eur = _decimal_env("MIN_EDGE_EUR", "0")

    horizon_hours_raw = os.getenv("EDGE_HORIZON_H", "24")
    try:
        horizon_hours = float(horizon_hours_raw)
    except ValueError:
        horizon_hours = 24.0
    horizon_hours = max(1.0, horizon_hours)

    capital_dec = Decimal(str(max(0.0, capital_eth)))
    delta_score = Decimal(str(max(0.0, score_best - score_current)))
    edge_eth = capital_dec * delta_score * Decimal(horizon_hours / 24.0)
    edge_eur = edge_eth * fx_rate

    gas_price = Decimal(str(w3.eth.gas_price))  # wei
    gas_eth = Decimal(est_move_gas) * gas_price / Decimal(10**18)
    gas_eur = gas_eth * fx_rate

    net_eur = edge_eur - gas_eur
    if net_eur < min_edge_eur:
        return False, (
            f"edge_insuff:{net_eur:.2f}€ (edge={edge_eur:.2f}€, gas={gas_eur:.2f}€)"
        )

    return True, f"edge_ok:{net_eur:.2f}€"
