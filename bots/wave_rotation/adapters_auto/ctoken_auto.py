#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Auto adapter for Compound v2 / Moonwell-like cTokens."""

from __future__ import annotations

from typing import Dict

from web3 import Web3

from abi_auto import CTOKEN_ABI, ERC20_ABI
from auto_utils import approve_max_if_needed, signer_send, wrap_to_target_if_needed


class CTokenAuto:
    @staticmethod
    def probe(w3: Web3, address: str) -> bool:
        try:
            token = w3.eth.contract(address=Web3.to_checksum_address(address), abi=CTOKEN_ABI)
            _ = token.functions.underlying().call()
            return True
        except Exception:
            return False

    def __init__(self, w3: Web3, signer, sender: str, address: str):
        self.w3 = w3
        self.signer = signer
        self.sender = Web3.to_checksum_address(sender)
        self.token = w3.eth.contract(address=Web3.to_checksum_address(address), abi=CTOKEN_ABI)
        asset_address = self.token.functions.underlying().call()
        self.asset = w3.eth.contract(address=asset_address, abi=ERC20_ABI)

    def deposit_all(self) -> Dict[str, object]:
        balance = self.asset.functions.balanceOf(self.sender).call()
        if balance == 0:
            try:
                decimals = self.asset.functions.decimals().call()
            except Exception:
                decimals = 18
            min_needed = 10 ** min(decimals, 6)
            wrap_to_target_if_needed(self.w3, self.signer, self.sender, self.asset.address, min_needed)
            balance = self.asset.functions.balanceOf(self.sender).call()
        if balance == 0:
            return {"status": "no_assets"}
        approve_tx = approve_max_if_needed(
            self.w3, self.signer, self.sender, self.asset.address, self.token.address, balance
        )
        tx = self.token.functions.mint(balance).build_transaction({"from": self.sender})
        deposit_tx = signer_send(self.w3, self.signer, tx)
        result = {"status": "ok", "deposit_tx": deposit_tx, "assets": int(balance)}
        if approve_tx:
            result["approve_tx"] = approve_tx
        return result

    def withdraw_all(self) -> Dict[str, object]:
        shares = self.token.functions.balanceOf(self.sender).call()
        if shares == 0:
            return {"status": "no_shares"}
        tx = self.token.functions.redeem(shares).build_transaction({"from": self.sender})
        withdraw_tx = signer_send(self.w3, self.signer, tx)
        return {"status": "ok", "withdraw_tx": withdraw_tx, "shares": int(shares)}
