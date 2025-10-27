#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Explicit adapter for Yearn-like vaults."""

from __future__ import annotations

from typing import Dict

from web3 import Web3

from abi_auto import ERC20_ABI, YEARN_ABI
from auto_utils import approve_max_if_needed, signer_send, wrap_to_target_if_needed
from .base import Adapter


class YearnAdapter(Adapter):
    """Interact with Yearn-style vaults using explicit configuration."""

    def __init__(self, w3: Web3, config: Dict[str, object], signer, sender: str):
        vault_addr = config.get("vault") or config.get("address")
        if not vault_addr:
            raise ValueError("Yearn adapter requires 'vault' address")

        self.w3 = w3
        self.signer = signer
        self.sender = Web3.to_checksum_address(sender)
        self.vault = w3.eth.contract(address=Web3.to_checksum_address(str(vault_addr)), abi=YEARN_ABI)

        asset_address = config.get("asset")
        if not asset_address:
            asset_address = self.vault.functions.token().call()
        self.asset = w3.eth.contract(address=Web3.to_checksum_address(str(asset_address)), abi=ERC20_ABI)

    # Helpers -------------------------------------------------------------
    def _asset_balance(self) -> int:
        return self.asset.functions.balanceOf(self.sender).call()

    # Adapter API ---------------------------------------------------------
    def deposit_all(self) -> Dict[str, object]:
        balance = self._asset_balance()
        if balance == 0:
            try:
                decimals = self.asset.functions.decimals().call()
            except Exception:
                decimals = 18
            minimum = 10 ** min(decimals, 6)
            try:
                wrap_to_target_if_needed(
                    self.w3, self.signer, self.sender, self.asset.address, minimum
                )
            except Exception as exc:
                return {"status": "error", "error": f"wrap_failed:{exc}"}
            balance = self._asset_balance()

        if balance == 0:
            return {"status": "no_assets"}

        result: Dict[str, object] = {"status": "ok", "assets": int(balance)}
        approve_tx = approve_max_if_needed(
            self.w3, self.signer, self.sender, self.asset.address, self.vault.address, balance
        )
        if approve_tx:
            result["approve_tx"] = approve_tx

        tx = self.vault.functions.deposit(balance).build_transaction({"from": self.sender})
        deposit_tx = signer_send(self.w3, self.signer, tx)
        result["deposit_tx"] = deposit_tx
        return result

    def withdraw_all(self) -> Dict[str, object]:
        shares = self.vault.functions.balanceOf(self.sender).call()
        if shares == 0:
            return {"status": "no_shares"}

        tx = self.vault.functions.withdraw(shares).build_transaction({"from": self.sender})
        withdraw_tx = signer_send(self.w3, self.signer, tx)
        return {"status": "ok", "withdraw_tx": withdraw_tx, "shares": int(shares)}
