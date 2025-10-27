#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Operational guardrails (gas ceiling, economic edge checks)."""

from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from typing import Tuple

try:  # Optional dependency – guard usage when web3 is unavailable
    from web3 import Web3
except ModuleNotFoundError:  # pragma: no cover - import guard branch
    Web3 = None  # type: ignore[assignment]


def _decimal_env(name: str, default: str) -> Decimal:
    raw = os.getenv(name, default)
    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError):
        return Decimal(default)


def gas_ceiling_ok(w3: Web3 | None) -> Tuple[bool, str]:
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

    if w3 is None:
        return False, "gas:web3_missing"

    gas_price_wei = w3.eth.gas_price
    gas_price_gwei = gas_price_wei / 1e9
    if gas_price_gwei > ceiling_gwei:
        return False, f"gas>{ceiling_gwei:g}gwei({gas_price_gwei:.2f})"
    return True, f"gas_ok:{gas_price_gwei:.2f}gwei"


def _as_decimal(value: float | int | Decimal | None) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _fmt(value: Decimal, places: int = 6) -> str:
    quant = Decimal(1).scaleb(-places)
    try:
        return format(value.quantize(quant), "f")
    except InvalidOperation:
        return format(value, "f")


def should_move(
    capital_eth: float,
    score_best: float,
    score_current: float | None,
    *,
    est_move_gas: int,
    w3: Web3 | None,
) -> Tuple[bool, str]:
    """Decide if the expected edge justifies switching pool."""

    delta = _as_decimal(score_best) - _as_decimal(score_current)
    if delta <= 0:
        return False, f"edge:delta<=0(delta={_fmt(delta)})"

    min_delta = _decimal_env("MIN_EDGE_SCORE", "0")
    if delta < min_delta:
        return False, f"edge:delta<{_fmt(min_delta)}(delta={_fmt(delta)})"

    capital = _as_decimal(capital_eth)
    expected_gain_eth = capital * delta
    if expected_gain_eth <= 0:
        return False, f"edge:gain<=0(gain={_fmt(expected_gain_eth)})"

    min_gain_eth = _decimal_env("MIN_EDGE_ETH", "0")
    if expected_gain_eth < min_gain_eth:
        return False, f"edge:gain_eth<{_fmt(min_gain_eth)}(gain={_fmt(expected_gain_eth)})"

    min_gain_usd = _decimal_env("MIN_EDGE_USD", "0")
    if min_gain_usd > 0:
        eth_price_usd = _decimal_env("ETH_PRICE_USD", "0")
        if eth_price_usd > 0:
            gain_usd = expected_gain_eth * eth_price_usd
            if gain_usd < min_gain_usd:
                return False, f"edge:gain_usd<{_fmt(min_gain_usd)}(gain={_fmt(gain_usd)})"

    gas_note = "gas=na"
    if w3 is not None:
        try:
            gas_price = _as_decimal(getattr(w3.eth, "gas_price"))
            gas_cost_eth = _as_decimal(est_move_gas) * gas_price / Decimal(10**18)
            gas_mult = _decimal_env("EDGE_GAS_MULTIPLIER", "1.0")
            if gas_mult <= 0:
                gas_mult = Decimal("1.0")
            required_gain = gas_cost_eth * gas_mult
            if expected_gain_eth <= required_gain:
                return False, f"edge:gas>{_fmt(required_gain)}(gain={_fmt(expected_gain_eth)})"
            gas_note = f"gas={_fmt(gas_cost_eth)}"
        except Exception:  # pragma: no cover - defensive path for unexpected RPC issues
            gas_note = "gas=error"
    else:
        gas_note = "gas=web3_missing"

    return True, f"edge:ok:delta={_fmt(delta)}:gain_eth={_fmt(expected_gain_eth)}:{gas_note}"
