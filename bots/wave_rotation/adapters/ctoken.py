#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Explicit adapter for Compound v2 / Moonwell style cTokens."""

from __future__ import annotations

from typing import Dict

from web3 import Web3

from abi_auto import CTOKEN_ABI, ERC20_ABI
from auto_utils import approve_max_if_needed, signer_send, wrap_to_target_if_needed
from .base import Adapter


class CTokenAdapter(Adapter):
    """Manage deposits into protocols that expose the classic cToken interface."""

    def __init__(self, w3: Web3, config: Dict[str, object], signer, sender: str):
        token_addr = config.get("ctoken") or config.get("token")
        if not token_addr:
            raise ValueError("CToken adapter requires 'ctoken' address")

        self.w3 = w3
        self.signer = signer
        self.sender = Web3.to_checksum_address(sender)
        self.token = w3.eth.contract(address=Web3.to_checksum_address(str(token_addr)), abi=CTOKEN_ABI)

        asset_address = config.get("asset") or config.get("underlying")
        if not asset_address:
            try:
                asset_address = self.token.functions.underlying().call()
            except Exception as exc:
                raise ValueError("CToken adapter requires 'asset' when underlying() is unavailable") from exc

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
            wrap_to_target_if_needed(self.w3, self.signer, self.sender, self.asset.address, minimum)
            balance = self._asset_balance()

        if balance == 0:
            return {"status": "no_assets"}

        result: Dict[str, object] = {"status": "ok", "assets": int(balance)}
        approve_tx = approve_max_if_needed(
            self.w3, self.signer, self.sender, self.asset.address, self.token.address, balance
        )
        if approve_tx:
            result["approve_tx"] = approve_tx

        tx = self.token.functions.mint(balance).build_transaction({"from": self.sender})
        deposit_tx = signer_send(self.w3, self.signer, tx)
        result["deposit_tx"] = deposit_tx
        return result

    def withdraw_all(self) -> Dict[str, object]:
        shares = self.token.functions.balanceOf(self.sender).call()
        if shares == 0:
            return {"status": "no_shares"}

        tx = self.token.functions.redeem(shares).build_transaction({"from": self.sender})
        withdraw_tx = signer_send(self.w3, self.signer, tx)
        return {"status": "ok", "withdraw_tx": withdraw_tx, "shares": int(shares)}
