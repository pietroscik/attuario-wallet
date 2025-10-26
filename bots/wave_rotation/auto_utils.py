#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Utility helpers shared across auto-adapters."""

from __future__ import annotations

import os
from web3 import Web3

from abi_auto import ERC20_ABI

MAX_UINT256 = (1 << 256) - 1
WETH_BY_CHAIN = {
    8453: "0x4200000000000000000000000000000000000006",  # Base
    1: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # Ethereum
}
WETH_ABI = [
    {
        "inputs": [],
        "name": "deposit",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    }
]


def _gas_reserve_wei() -> int:
    reserve_eth = os.getenv("GAS_RESERVE_ETH")
    if reserve_eth:
        try:
            return int(float(reserve_eth) * 1e18)
        except ValueError:
            pass
    reserve_wei = os.getenv("GAS_RESERVE_WEI")
    if reserve_wei:
        try:
            return int(reserve_wei)
        except ValueError:
            pass
    return 20_000_000_000_000_000  # 0.02 ETH default


def signer_send(w3: Web3, signer, tx: dict) -> str:
    tx.setdefault("chainId", w3.eth.chain_id)
    tx.setdefault("nonce", w3.eth.get_transaction_count(tx["from"]))
    if "gas" not in tx:
        tx["gas"] = w3.eth.estimate_gas(tx)
    gas_price = w3.eth.gas_price
    tx.setdefault("maxFeePerGas", gas_price)
    tx.setdefault("maxPriorityFeePerGas", gas_price)
    call_tx = {k: tx[k] for k in ("to", "from", "data") if k in tx}
    call_tx["value"] = tx.get("value", 0)
    w3.eth.call(call_tx)
    signed = signer.sign_transaction(tx)
    return w3.eth.send_raw_transaction(signed.rawTransaction).hex()


def approve_max_if_needed(w3: Web3, signer, sender: str, token: str, spender: str, amount: int):
    contract = w3.eth.contract(address=Web3.to_checksum_address(token), abi=ERC20_ABI)
    allowance = contract.functions.allowance(sender, spender).call()
    if allowance >= amount:
        return None
    tx = contract.functions.approve(spender, MAX_UINT256).build_transaction({"from": sender})
    return signer_send(w3, signer, tx)


def wrap_to_target_if_needed(
    w3: Web3,
    signer,
    sender: str,
    target_token: str,
    target_needed_wei: int,
) -> None:
    weth_addr = WETH_BY_CHAIN.get(w3.eth.chain_id)
    if not weth_addr:
        return None
    if Web3.to_checksum_address(target_token) != Web3.to_checksum_address(weth_addr):
        return None

    contract = w3.eth.contract(address=weth_addr, abi=ERC20_ABI)
    current_balance = contract.functions.balanceOf(sender).call()
    deficit = max(0, int(target_needed_wei) - int(current_balance))
    if deficit <= 0:
        return None

    balance_eth = w3.eth.get_balance(sender)
    reserve = _gas_reserve_wei()
    max_available = max(0, balance_eth - reserve)
    pct_raw = os.getenv("MAX_WRAP_PCT", "0.8")
    try:
        pct = float(pct_raw)
    except ValueError:
        pct = 0.8
    allowed = int(max_available * max(0.0, min(1.0, pct)))
    amount = min(deficit, allowed)
    if amount <= 0:
        return None

    weth_contract = w3.eth.contract(address=weth_addr, abi=WETH_ABI)
    tx = weth_contract.functions.deposit().build_transaction({"from": sender, "value": amount})
    return signer_send(w3, signer, tx)
