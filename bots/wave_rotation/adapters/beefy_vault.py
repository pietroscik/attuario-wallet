#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Adapter for Beefy vaults on various chains (extending existing lp_beefy_aero)."""

from __future__ import annotations

import math
import os
from decimal import Decimal
from typing import Dict, Optional

from web3 import Web3
from web3.contract.contract import Contract

from abi_min import ERC20_ABI
from .base import Adapter

MAX_UINT256 = (1 << 256) - 1


BEEFY_VAULT_ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "_amount", "type": "uint256"}],
        "name": "deposit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_shares", "type": "uint256"}],
        "name": "withdraw",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "want",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def _contract(w3: Web3, address: str, abi) -> Contract:
    return w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)


def _balance(token: Contract, owner: str) -> int:
    return token.functions.balanceOf(owner).call()


def _sign_and_send(w3: Web3, signer, tx: Dict[str, object], *, nonce: Optional[int] = None) -> str:
    tx.setdefault("from", signer.address)
    tx.setdefault("chainId", w3.eth.chain_id)
    if nonce is None:
        nonce = w3.eth.get_transaction_count(signer.address)
    tx["nonce"] = nonce

    if "gas" not in tx:
        tx["gas"] = w3.eth.estimate_gas(tx)
    gas_price = w3.eth.gas_price
    tx.setdefault("maxFeePerGas", gas_price)
    tx.setdefault("maxPriorityFeePerGas", gas_price)

    call_tx = {k: tx[k] for k in ("to", "from", "data") if k in tx}
    call_tx["value"] = tx.get("value", 0)
    w3.eth.call(call_tx)

    signed = signer.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return tx_hash.hex()


def _approve_if_needed(
    w3: Web3,
    signer,
    token: Contract,
    spender: str,
    amount: int,
    *,
    nonce: Optional[int] = None,
) -> Optional[str]:
    current = token.functions.allowance(signer.address, spender).call()
    if current >= amount:
        return None
    mode = os.getenv("ALLOWANCE_MODE", "MAX").strip().upper()
    approve_amount = MAX_UINT256 if mode == "MAX" else amount
    tx = token.functions.approve(spender, approve_amount).build_transaction({"from": signer.address})
    return _sign_and_send(w3, signer, tx, nonce=nonce)


class BeefyVaultAdapter(Adapter):
    """
    Generic Beefy vault adapter for single-sided or auto-compounding vaults.
    
    For LP token vaults wrapped by Beefy, use lp_beefy_aero for Aerodrome-based
    or create specific adapters for other DEXes.
    
    This adapter handles simple deposit/withdraw to Beefy vaults where the want
    token is provided directly (e.g., single-sided staking).
    """

    def __init__(self, w3: Web3, config: Dict[str, object], signer, sender: str):
        self.w3 = w3
        self.signer = signer
        self.sender = Web3.to_checksum_address(sender)

        try:
            self.vault_address = str(config["vault"])
        except KeyError as exc:
            raise RuntimeError(f"[beefy_vault] missing configuration field: {exc.args[0]}")

        self.vault = _contract(w3, self.vault_address, BEEFY_VAULT_ABI)
        want_address = self.vault.functions.want().call()
        self.want = _contract(w3, want_address, ERC20_ABI)

    def deposit_all(self) -> Dict[str, object]:
        want_balance = _balance(self.want, self.sender)
        notes: list[str] = []

        if want_balance == 0:
            return {"status": "no_assets", "want": self.want.address}

        nonce = self.w3.eth.get_transaction_count(self.sender)
        approve_hash = _approve_if_needed(
            self.w3, self.signer, self.want, self.vault_address, want_balance, nonce=nonce
        )
        if approve_hash:
            notes.append(f"approve_want:{approve_hash}")
            nonce += 1

        deposit_tx = self.vault.functions.deposit(want_balance).build_transaction({"from": self.sender})
        deposit_hash = _sign_and_send(self.w3, self.signer, deposit_tx, nonce=nonce)
        notes.append(f"beefy.deposit:{deposit_hash}")

        return {
            "status": "ok",
            "deposit_tx": deposit_hash,
            "notes": notes,
            "assets_used": {"want": want_balance},
        }

    def withdraw_all(self) -> Dict[str, object]:
        shares = self.vault.functions.balanceOf(self.sender).call()
        notes: list[str] = []

        if shares == 0:
            return {"status": "no_shares"}

        withdraw_tx = self.vault.functions.withdraw(shares).build_transaction({"from": self.sender})
        nonce = self.w3.eth.get_transaction_count(self.sender)
        withdraw_hash = _sign_and_send(self.w3, self.signer, withdraw_tx, nonce=nonce)
        notes.append(f"beefy.withdraw:{withdraw_hash}")

        return {
            "status": "ok",
            "withdraw_tx": withdraw_hash,
            "notes": notes,
            "shares": shares,
        }
