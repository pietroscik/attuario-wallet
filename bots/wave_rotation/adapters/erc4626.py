#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""ERC-4626 adapter implementing deposit/withdraw all operations."""

from __future__ import annotations

import os
from typing import Dict, Optional

from web3 import Web3

from abi_min import ERC20_ABI, ERC4626_ABI
from .base import Adapter


MAX_UINT256 = (1 << 256) - 1


class ERC4626Adapter(Adapter):
    def __init__(self, w3: Web3, config: Dict[str, object], signer, sender: str):
        self.w3 = w3
        self.signer = signer
        self.sender = Web3.to_checksum_address(sender)
        self.vault = w3.eth.contract(
            address=Web3.to_checksum_address(str(config["vault"])), abi=ERC4626_ABI
        )
        self.asset = w3.eth.contract(
            address=Web3.to_checksum_address(str(config["asset"])), abi=ERC20_ABI
        )

    # Common helpers -----------------------------------------------------
    def _get_nonce(self) -> int:
        return self.w3.eth.get_transaction_count(self.sender)

    def _simulate(self, tx: Dict[str, object]) -> None:
        call_tx = {k: tx[k] for k in ("to", "from", "data") if k in tx}
        call_tx["value"] = tx.get("value", 0)
        self.w3.eth.call(call_tx)

    def _sign_and_send(self, tx: Dict[str, object], nonce: Optional[int] = None) -> str:
        tx.setdefault("chainId", self.w3.eth.chain_id)
        tx.setdefault("from", self.sender)
        if nonce is None:
            nonce = self._get_nonce()
        tx["nonce"] = nonce

        if "gas" not in tx:
            tx["gas"] = self.w3.eth.estimate_gas(tx)

        gas_price = self.w3.eth.gas_price
        if "maxFeePerGas" not in tx:
            tx["maxFeePerGas"] = gas_price
        if "maxPriorityFeePerGas" not in tx:
            tx["maxPriorityFeePerGas"] = gas_price

        self._simulate(tx)

        signed = self.signer.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    # Token allowances / balances ---------------------------------------
    def _allowance(self) -> int:
        return self.asset.functions.allowance(self.sender, self.vault.address).call()

    def _approve_if_needed(self, amount: int, nonce: int) -> Optional[str]:
        allowance = self._allowance()
        if allowance >= amount:
            return None

        mode = os.getenv("ALLOWANCE_MODE", "MAX").strip().upper()
        approve_amount = MAX_UINT256 if mode == "MAX" else amount

        tx = self.asset.functions.approve(self.vault.address, approve_amount).build_transaction(
            {"from": self.sender}
        )
        return self._sign_and_send(tx, nonce=nonce)

    def _asset_balance(self) -> int:
        return self.asset.functions.balanceOf(self.sender).call()

    def _max_redeem(self) -> int:
        return self.vault.functions.maxRedeem(self.sender).call()

    # Adapter API --------------------------------------------------------
    def deposit_all(self) -> Dict[str, object]:
        amount = self._asset_balance()
        if amount <= 0:
            return {"status": "no_assets"}

        operations: Dict[str, object] = {"status": "ok", "assets": int(amount)}

        nonce = self._get_nonce()
        approve_hash = self._approve_if_needed(amount, nonce)
        if approve_hash:
            operations["approve_tx"] = approve_hash
            nonce += 1

        deposit_tx = self.vault.functions.deposit(amount, self.sender).build_transaction(
            {"from": self.sender}
        )
        deposit_hash = self._sign_and_send(deposit_tx, nonce=nonce)
        operations["deposit_tx"] = deposit_hash
        return operations

    def withdraw_all(self) -> Dict[str, object]:
        shares = self._max_redeem()
        if shares <= 0:
            return {"status": "no_shares"}

        withdraw_tx = self.vault.functions.redeem(
            shares, self.sender, self.sender
        ).build_transaction({"from": self.sender})
        nonce = self._get_nonce()
        withdraw_hash = self._sign_and_send(withdraw_tx, nonce=nonce)
        return {"status": "ok", "withdraw_tx": withdraw_hash, "shares": int(shares)}
