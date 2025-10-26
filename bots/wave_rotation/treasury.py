#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Treasury payout helpers: swap ETH profit to EURC and send to treasury."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Dict, Optional

import requests
from web3 import Web3

from onchain import get_available_capital_eth, get_signer_context

EURC_BASE_ADDRESS = os.getenv(
    "TREASURY_TOKEN_ADDRESS",
    "0xAdC42D37c9E07B440b0d0F15B93bb3f379f73d6c",
)
ZEROX_BASE_URL = os.getenv("TREASURY_SWAP_API", "https://base.api.0x.org/swap/v1/quote")
ERC20_ABI = json.loads(
    """
[
  {
    "constant": true,
    "inputs": [{"name": "owner", "type": "address"}],
    "name": "balanceOf",
    "outputs": [{"name": "balance", "type": "uint256"}],
    "payable": false,
    "stateMutability": "view",
    "type": "function"
  },
  {
    "constant": false,
    "inputs": [
      {"name": "to", "type": "address"},
      {"name": "value", "type": "uint256"}
    ],
    "name": "transfer",
    "outputs": [{"name": "", "type": "bool"}],
    "payable": false,
    "stateMutability": "nonpayable",
    "type": "function"
  }
]
"""
)


@dataclass
class TreasurySettings:
    address: str
    eurc_address: str
    swap_api: str
    slippage_bps: int
    min_swap_eth: Decimal
    gas_reserve_eth: Decimal
    wait_timeout: int = 180


def _decimal_env(name: str, default: str) -> Decimal:
    raw = os.getenv(name, default)
    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError):
        return Decimal(str(default))


def load_settings() -> Optional[TreasurySettings]:
    if os.getenv("TREASURY_AUTOMATION_ENABLED", "false").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return None

    address = os.getenv("TREASURY_ADDRESS")
    if not address:
        return None

    min_swap = _decimal_env("MIN_TREASURY_SWAP_ETH", "0.0005")
    slippage_bps_raw = os.getenv("SWAP_SLIPPAGE_BPS", "100")
    try:
        slippage_bps = int(slippage_bps_raw)
    except ValueError:
        slippage_bps = 100

    gas_reserve = _decimal_env("GAS_RESERVE_ETH", "0.004")

    return TreasurySettings(
        address=Web3.to_checksum_address(address),
        eurc_address=Web3.to_checksum_address(EURC_BASE_ADDRESS),
        swap_api=ZEROX_BASE_URL.rstrip("/"),
        slippage_bps=max(10, slippage_bps),
        min_swap_eth=min_swap,
        gas_reserve_eth=gas_reserve,
    )


def _fetch_quote(
    sell_amount_wei: int, settings: TreasurySettings, account_address: str
) -> Optional[Dict[str, str]]:
    params = {
        "sellToken": "ETH",
        "buyToken": settings.eurc_address,
        "sellAmount": str(sell_amount_wei),
        "takerAddress": account_address,
        "slippagePercentage": str(Decimal(settings.slippage_bps) / Decimal("10000")),
    }
    headers: Dict[str, str] = {}
    api_key = os.getenv("TREASURY_SWAP_API_KEY") or os.getenv("ZEROX_API_KEY")
    if api_key:
        headers["0x-api-key"] = api_key

    try:
        resp = requests.get(settings.swap_api, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[treasury] swap quote failed: {exc}")
        return None

    try:
        payload = resp.json()
    except ValueError:
        print("[treasury] invalid JSON from swap API")
        return None
    required = {"to", "data", "value", "buyAmount"}
    if not required.issubset(payload):
        print("[treasury] incomplete quote:", payload)
        return None
    return payload


def _int_safe(value) -> int:
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _wei(amount_eth: Decimal) -> int:
    wei = (amount_eth * Decimal("1e18")).to_integral_value(rounding=ROUND_DOWN)
    return max(0, int(wei))


def dispatch_treasury_payout(profit_eth: float) -> Optional[Dict[str, object]]:
    """
    Swap the treasury share of profit into EURC and transfer to treasury.
    Returns dictionary with tx hashes on success, None if disabled, or {}
    if skipped due to thresholds.
    """
    settings = load_settings()
    if settings is None:
        return None

    profit_dec = Decimal(str(profit_eth))
    if profit_dec <= 0:
        return {}

    if profit_dec < settings.min_swap_eth:
        print(
            "[treasury] skipped: profit below min swap threshold "
            f"{settings.min_swap_eth} ETH"
        )
        return {}

    ctx = get_signer_context()
    if ctx is None:
        print("[treasury] signer context unavailable, cannot dispatch treasury payout.")
        return {}
    cfg, w3, account = ctx

    available = get_available_capital_eth(float(settings.gas_reserve_eth))
    if available is not None and profit_dec > Decimal(str(available)):
        print(
            "[treasury] skipped: not enough ETH above reserve for treasury payout "
            f"(profit {profit_dec} ETH, available {available} ETH)."
        )
        return {}

    sell_amount_wei = _wei(profit_dec)
    if sell_amount_wei == 0:
        print("[treasury] skipped: profit too small once converted to wei.")
        return {}

    quote = _fetch_quote(sell_amount_wei, settings, account.address)
    if quote is None:
        return {}

    eurc_contract = w3.eth.contract(address=settings.eurc_address, abi=ERC20_ABI)
    balance_before = eurc_contract.functions.balanceOf(account.address).call()

    nonce = w3.eth.get_transaction_count(account.address)
    gas_limit = _int_safe(quote.get("gas"))
    if gas_limit <= 0:
        try:
            gas_limit = w3.eth.estimate_gas(
                {
                    "to": Web3.to_checksum_address(quote["to"]),
                    "from": account.address,
                    "value": _int_safe(quote["value"]),
                    "data": quote["data"],
                }
            )
        except Exception as exc:
            print(f"[treasury] gas estimation failed: {exc}")
            return {}
    gas_price = _int_safe(quote.get("gasPrice")) or w3.eth.gas_price

    tx = {
        "chainId": w3.eth.chain_id,
        "from": account.address,
        "to": Web3.to_checksum_address(quote["to"]),
        "nonce": nonce,
        "data": quote["data"],
        "value": _int_safe(quote["value"]),
        "gas": int(Decimal(str(gas_limit)) * Decimal("1.1")),
        "gasPrice": int(gas_price),
    }

    try:
        signed = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        print(f"[treasury] swap sent: {tx_hash.hex()}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=settings.wait_timeout)
        if receipt.status != 1:
            print("[treasury] swap reverted, aborting treasury transfer.")
            return {}
    except Exception as exc:
        print(f"[treasury] swap failed: {exc}")
        return {}

    balance_after = eurc_contract.functions.balanceOf(account.address).call()
    acquired_eurc = max(0, balance_after - balance_before)
    if acquired_eurc == 0:
        print("[treasury] swap produced zero EURC, skipping transfer.")
        return {}

    transfer_amount = acquired_eurc
    transfer_fn = eurc_contract.functions.transfer(settings.address, transfer_amount)
    try:
        transfer_gas = transfer_fn.estimate_gas({"from": account.address})
    except Exception as exc:
        print(f"[treasury] transfer gas estimation failed: {exc}")
        return {"swap_tx": tx_hash.hex(), "swap_eurc_units": acquired_eurc}

    try:
        transfer_nonce = w3.eth.get_transaction_count(account.address)
        transfer_tx = transfer_fn.build_transaction(
            {
                "chainId": w3.eth.chain_id,
                "from": account.address,
                "nonce": transfer_nonce,
                "gas": int(Decimal(str(transfer_gas)) * Decimal("1.1")),
                "gasPrice": w3.eth.gas_price,
            }
        )
        signed_transfer = account.sign_transaction(transfer_tx)
        transfer_hash = w3.eth.send_raw_transaction(signed_transfer.rawTransaction)
        print(f"[treasury] transfer sent: {transfer_hash.hex()}")
        receipt_transfer = w3.eth.wait_for_transaction_receipt(
            transfer_hash, timeout=settings.wait_timeout
        )
        if receipt_transfer.status != 1:
            print("[treasury] transfer reverted.")
            return {
                "swap_tx": tx_hash.hex(),
                "swap_eurc_units": acquired_eurc,
                "transfer_tx": transfer_hash.hex(),
                "transfer_status": "reverted",
            }
    except Exception as exc:
        print(f"[treasury] transfer failed: {exc}")
        return {
            "swap_tx": tx_hash.hex(),
            "swap_eurc_units": acquired_eurc,
        }

    eurc_amount = Decimal(transfer_amount) / Decimal("1e6")
    return {
        "swap_tx": tx_hash.hex(),
        "transfer_tx": transfer_hash.hex(),
        "eurc_amount": float(eurc_amount),
        "swap_eurc_units": transfer_amount,
    }
