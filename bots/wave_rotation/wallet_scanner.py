#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Wallet scanning utilities for multi-strategy execution."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple, Union

try:
    from web3 import Web3  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Web3 = None  # type: ignore[assignment]

from adapter_utils import gather_required_token_labels

ERC20_BALANCE_DECIMALS_ABI = json.loads(
    """
[
  {
    "constant": true,
    "inputs": [{"name": "account", "type": "address"}],
    "name": "balanceOf",
    "outputs": [{"name": "", "type": "uint256"}],
    "payable": false,
    "stateMutability": "view",
    "type": "function"
  },
  {
    "constant": true,
    "inputs": [],
    "name": "decimals",
    "outputs": [{"name": "", "type": "uint8"}],
    "payable": false,
    "stateMutability": "view",
    "type": "function"
  }
]
"""
)


@dataclass
class WalletHolding:
    """Normalized wallet holding with USD valuation."""

    address: str
    label: str
    amount: float
    usd_value: float
    unit_price_usd: float
    is_native: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "address": self.address,
            "label": self.label,
            "amount": self.amount,
            "usd_value": self.usd_value,
            "unit_price_usd": self.unit_price_usd,
            "is_native": self.is_native,
        }


def _resolve_account_address(account_address: Optional[str]) -> Optional[str]:
    if account_address is None or Web3 is None:
        return account_address
    try:
        return Web3.to_checksum_address(account_address)
    except Exception:
        return account_address


def _collect_raw_balances(
    token_labels: Dict[str, str],
    w3,
    account_address: Optional[str],
) -> Dict[str, float]:
    balances = {key: 0.0 for key in token_labels}
    if w3 is None or Web3 is None or account_address is None:
        return balances

    checksum_account = _resolve_account_address(account_address)
    if checksum_account is None:
        return balances

    try:
        native_balance = w3.eth.get_balance(checksum_account)
        balances["native"] = float(Web3.from_wei(native_balance, "ether"))
    except Exception:
        balances["native"] = balances.get("native", 0.0)

    decimals_cache: Dict[str, int] = {}
    for addr in token_labels:
        if addr == "native":
            continue
        try:
            checksum_token = Web3.to_checksum_address(addr)
        except Exception:
            checksum_token = addr
        try:
            contract = w3.eth.contract(address=checksum_token, abi=ERC20_BALANCE_DECIMALS_ABI)
            if addr not in decimals_cache:
                decimals_cache[addr] = contract.functions.decimals().call()
            decimals = decimals_cache[addr]
            raw_balance = contract.functions.balanceOf(checksum_account).call()
            balances[addr] = float(raw_balance) / (10 ** decimals)
        except Exception:
            balances.setdefault(addr, 0.0)
    return balances


def _stable_addresses_from_env() -> Iterable[Tuple[str, float]]:
    """Return iterable of (address_lower, price_usd) for known stables."""
    stable_map = {
        "USDC_BASE": 1.0,
        "USDBC_BASE": 1.0,
        "USDT_BASE": 1.0,
        "EURC_BASE": float(os.getenv("EURC_USD_PRICE", "1.08")),
    }
    for env_name, default_price in stable_map.items():
        addr = os.getenv(env_name)
        if addr:
            yield addr.lower(), default_price


def _build_price_map(
    token_labels: Dict[str, str],
    *,
    eth_price_usd: float,
) -> Dict[str, float]:
    """Build simple price map using env overrides and known stables."""
    prices: Dict[str, float] = {}

    # Native and wrapped ETH share the same price
    prices["native"] = eth_price_usd
    for addr, label in token_labels.items():
        lbl_lower = label.lower()
        addr_lower = addr.lower()
        if "weth" in lbl_lower or "eth" == lbl_lower:
            prices[addr_lower] = eth_price_usd

    for addr_lower, price in _stable_addresses_from_env():
        prices.setdefault(addr_lower, price)

    # Allow overrides via PRICE_OVERRIDE_<TOKEN>=value
    prefix = "PRICE_OVERRIDE_"
    for name, value in os.environ.items():
        if not name.startswith(prefix):
            continue
        token_hint = name[len(prefix):].strip().lower()
        try:
            override = float(value)
        except (TypeError, ValueError):
            continue
        for addr, label in token_labels.items():
            addr_lower = addr.lower()
            if token_hint in {addr_lower, label.lower()}:
                prices[addr_lower] = override

    return prices


def _get_price_for_token(
    address: str,
    label: str,
    price_map: Dict[str, float],
    fallback: float,
) -> float:
    addr_lower = address.lower()
    lbl_lower = label.lower()
    if addr_lower in price_map:
        return price_map[addr_lower]
    return price_map.get(lbl_lower, fallback)


def scan_wallet(
    config: Union[Dict[str, object], object],
    w3,
    account_address: Optional[str],
    *,
    min_dust_usd: Optional[float] = None,
    eth_price_usd: Optional[float] = None,
) -> Tuple[List[WalletHolding], Dict[str, float], Dict[str, str]]:
    """
    Scan wallet balances and return normalized holdings and raw balances.

    Args:
        config: Strategy configuration (StrategyConfig dataclass or plain dict)
        w3: Optional Web3 instance
        account_address: Wallet address
        min_dust_usd: Minimum USD value to keep (defaults to env MIN_DUST_USD)
        eth_price_usd: Override ETH price (defaults to env ETH_PRICE_USD)

    Returns:
        Tuple of (holdings list, balances dict, labels dict)
    """
    min_dust = float(os.getenv("MIN_DUST_USD", "0.25")) if min_dust_usd is None else float(min_dust_usd)
    eth_price = float(os.getenv("ETH_PRICE_USD", "3000.0")) if eth_price_usd is None else float(eth_price_usd)

    token_labels = gather_required_token_labels(config)
    token_labels["native"] = "ETH"

    balances = _collect_raw_balances(token_labels, w3, account_address)

    price_map = _build_price_map(token_labels, eth_price_usd=eth_price)
    fallback_price = eth_price

    holdings: List[WalletHolding] = []

    for addr, label in token_labels.items():
        amount = balances.get(addr, 0.0)
        is_native = addr == "native"
        if amount <= 0:
            continue
        price = _get_price_for_token(addr, label, price_map, fallback_price)
        usd_value = amount * price
        if usd_value < min_dust:
            continue
        holding = WalletHolding(
            address=addr,
            label=label,
            amount=amount,
            usd_value=usd_value,
            unit_price_usd=price,
            is_native=is_native,
        )
        holdings.append(holding)

    holdings.sort(key=lambda h: h.usd_value, reverse=True)

    return holdings, balances, token_labels


def collect_wallet_assets(
    config: Union[Dict[str, object], object],
    w3,
    account_address: Optional[str],
) -> Tuple[Dict[str, float], Dict[str, str]]:
    """
    Backwards-compatible helper returning raw balances/labels.

    Used by legacy rotation path that expects the original return signature.
    """
    _, balances, labels = scan_wallet(
        config,
        w3,
        account_address,
        min_dust_usd=0.0,
    )
    return balances, labels
