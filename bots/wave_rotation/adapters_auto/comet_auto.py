#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Auto adapter for Compound v3 (Comet) markets."""

from __future__ import annotations

from typing import Dict

from web3 import Web3

from abi_auto import COMET_ABI, ERC20_ABI
from auto_utils import approve_max_if_needed, signer_send, wrap_to_target_if_needed


class CometAuto:
    @staticmethod
    def probe(w3: Web3, address: str) -> bool:
        try:
            comet = w3.eth.contract(address=Web3.to_checksum_address(address), abi=COMET_ABI)
            _ = comet.functions.baseToken().call()
            return True
        except Exception:
            return False

    def __init__(self, w3: Web3, signer, sender: str, address: str):
        self.w3 = w3
        self.signer = signer
        self.sender = Web3.to_checksum_address(sender)
        self.comet = w3.eth.contract(address=Web3.to_checksum_address(address), abi=COMET_ABI)
        asset_address = self.comet.functions.baseToken().call()
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
            self.w3, self.signer, self.sender, self.asset.address, self.comet.address, balance
        )
        tx = self.comet.functions.supply(self.asset.address, balance).build_transaction({"from": self.sender})
        deposit_tx = signer_send(self.w3, self.signer, tx)
        result = {"status": "ok", "deposit_tx": deposit_tx, "assets": int(balance)}
        if approve_tx:
            result["approve_tx"] = approve_tx
        return result

    def withdraw_all(self) -> Dict[str, object]:
        max_uint = (1 << 256) - 1
        tx = self.comet.functions.withdraw(self.asset.address, max_uint).build_transaction(
            {"from": self.sender}
        )
        withdraw_tx = signer_send(self.w3, self.signer, tx)
        return {"status": "ok", "withdraw_tx": withdraw_tx}
