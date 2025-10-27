#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Explicit adapter for supplying / withdrawing on Aave v3."""

from __future__ import annotations

import os
from typing import Dict, Optional

from web3 import Web3

from abi_min import ERC20_ABI
from .base import Adapter

MAX_UINT256 = (1 << 256) - 1

AAVE_POOL_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "asset", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "address", "name": "onBehalfOf", "type": "address"},
            {"internalType": "uint16", "name": "referralCode", "type": "uint16"},
        ],
        "name": "supply",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "asset", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "address", "name": "to", "type": "address"},
        ],
        "name": "withdraw",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "asset", "type": "address"},
            {"internalType": "address", "name": "user", "type": "address"},
        ],
        "name": "getUserReserveData",
        "outputs": [
            {"internalType": "uint256", "name": "currentATokenBalance", "type": "uint256"},
            {"internalType": "uint256", "name": "currentStableDebt", "type": "uint256"},
            {"internalType": "uint256", "name": "currentVariableDebt", "type": "uint256"},
            {"internalType": "uint256", "name": "principalStableDebt", "type": "uint256"},
            {"internalType": "uint256", "name": "scaledStableDebt", "type": "uint256"},
            {"internalType": "uint256", "name": "scaledVariableDebt", "type": "uint256"},
            {"internalType": "uint256", "name": "liquidityRate", "type": "uint256"},
            {"internalType": "uint256", "name": "variableBorrowRate", "type": "uint256"},
            {"internalType": "uint256", "name": "stableBorrowRate", "type": "uint256"},
            {"internalType": "uint40", "name": "lastUpdateTimestamp", "type": "uint40"},
            {"internalType": "bool", "name": "usageAsCollateralEnabled", "type": "bool"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


class AaveV3Adapter(Adapter):
    """Adapter that supplies/withdraws a single asset on Aave v3."""

    def __init__(self, w3, config: Dict[str, object], signer, sender: str):
        pool_address = str(config.get("pool") or "").strip()
        asset_address = str(config.get("asset") or "").strip()
        if not pool_address:
            raise ValueError("Aave adapter requires 'pool' address")
        if not asset_address:
            raise ValueError("Aave adapter requires 'asset' address")

        self.w3 = w3
        self.signer = signer
        self.sender = Web3.to_checksum_address(sender)
        self.pool = w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=AAVE_POOL_ABI,
        )
        self.asset = w3.eth.contract(
            address=Web3.to_checksum_address(asset_address),
            abi=ERC20_ABI,
        )
        self.referral_code = int(config.get("referral_code") or 0)

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #
    def _get_nonce(self) -> int:
        return self.w3.eth.get_transaction_count(self.sender)

    def _sign_and_send(self, tx: Dict[str, object], *, nonce: Optional[int] = None) -> str:
        tx.setdefault("chainId", self.w3.eth.chain_id)
        tx.setdefault("from", self.sender)
        if nonce is None:
            nonce = self._get_nonce()
        tx["nonce"] = nonce

        if "gas" not in tx:
            tx["gas"] = self.w3.eth.estimate_gas(tx)

        gas_price = self.w3.eth.gas_price
        tx.setdefault("maxFeePerGas", gas_price)
        tx.setdefault("maxPriorityFeePerGas", gas_price)

        # Dry simulation before sending (raises on failure)
        call_tx = {k: tx[k] for k in ("to", "from", "data") if k in tx}
        call_tx["value"] = tx.get("value", 0)
        self.w3.eth.call(call_tx)

        signed = self.signer.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    def _allowance(self) -> int:
        return self.asset.functions.allowance(self.sender, self.pool.address).call()

    def _approve_if_needed(self, amount: int, nonce: int) -> Optional[str]:
        allowance = self._allowance()
        if allowance >= amount:
            return None

        mode = os.getenv("ALLOWANCE_MODE", "MAX").strip().upper()
        approve_amount = MAX_UINT256 if mode == "MAX" else amount
        tx = self.asset.functions.approve(self.pool.address, approve_amount).build_transaction(
            {"from": self.sender}
        )
        return self._sign_and_send(tx, nonce=nonce)

    def _asset_balance(self) -> int:
        return self.asset.functions.balanceOf(self.sender).call()

    def _a_token_balance(self) -> int:
        data = self.pool.functions.getUserReserveData(self.asset.address, self.sender).call()
        return int(data[0])

    # ------------------------------------------------------------------ #
    # Adapter API                                                        #
    # ------------------------------------------------------------------ #
    def deposit_all(self) -> Dict[str, object]:
        amount = self._asset_balance()
        if amount <= 0:
            return {"status": "no_assets"}

        result: Dict[str, object] = {"status": "ok", "assets": int(amount)}
        nonce = self._get_nonce()

        approve_hash = self._approve_if_needed(amount, nonce)
        if approve_hash:
            result["approve_tx"] = approve_hash
            nonce += 1

        tx = self.pool.functions.supply(
            self.asset.address,
            int(amount),
            self.sender,
            self.referral_code,
        ).build_transaction({"from": self.sender})
        result["supply_tx"] = self._sign_and_send(tx, nonce=nonce)
        return result

    def withdraw_all(self) -> Dict[str, object]:
        shares = self._a_token_balance()
        if shares <= 0:
            return {"status": "no_shares"}

        tx = self.pool.functions.withdraw(
            self.asset.address,
            MAX_UINT256,
            self.sender,
        ).build_transaction({"from": self.sender})
        withdraw_hash = self._sign_and_send(tx, nonce=self._get_nonce())
        return {
            "status": "ok",
            "withdraw_tx": withdraw_hash,
            "shares": int(shares),
        }
