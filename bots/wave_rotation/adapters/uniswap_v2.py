#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Adapter for Uniswap v2 style LP pools (also compatible with forks like BaseSwap, SushiSwap, etc.)."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional

from web3 import Web3
from web3.contract.contract import Contract

from abi_min import ERC20_ABI
from .base import Adapter

MAX_UINT256 = (1 << 256) - 1


UNISWAP_V2_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"},
            {"internalType": "uint256", "name": "amountADesired", "type": "uint256"},
            {"internalType": "uint256", "name": "amountBDesired", "type": "uint256"},
            {"internalType": "uint256", "name": "amountAMin", "type": "uint256"},
            {"internalType": "uint256", "name": "amountBMin", "type": "uint256"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
        ],
        "name": "addLiquidity",
        "outputs": [
            {"internalType": "uint256", "name": "amountA", "type": "uint256"},
            {"internalType": "uint256", "name": "amountB", "type": "uint256"},
            {"internalType": "uint256", "name": "liquidity", "type": "uint256"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"},
            {"internalType": "uint256", "name": "liquidity", "type": "uint256"},
            {"internalType": "uint256", "name": "amountAMin", "type": "uint256"},
            {"internalType": "uint256", "name": "amountBMin", "type": "uint256"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
        ],
        "name": "removeLiquidity",
        "outputs": [
            {"internalType": "uint256", "name": "amountA", "type": "uint256"},
            {"internalType": "uint256", "name": "amountB", "type": "uint256"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


def _contract(w3: Web3, address: str, abi) -> Contract:
    return w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)


def _allowance(token: Contract, owner: str, spender: str) -> int:
    return token.functions.allowance(owner, spender).call()


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
    current = _allowance(token, signer.address, spender)
    if current >= amount:
        return None
    mode = os.getenv("ALLOWANCE_MODE", "MAX").strip().upper()
    approve_amount = MAX_UINT256 if mode == "MAX" else amount
    tx = token.functions.approve(spender, approve_amount).build_transaction({"from": signer.address})
    return _sign_and_send(w3, signer, tx, nonce=nonce)


@dataclass
class UniswapV2Config:
    router: str
    lp_token: str
    token0: str
    token1: str
    slippage_bps: int


def _load_config(raw: Dict[str, object]) -> UniswapV2Config:
    try:
        router = raw["router"]
        lp_token = raw["lp_token"]
        token0 = raw["token0"]
        token1 = raw["token1"]
    except KeyError as exc:
        raise RuntimeError(f"[uniswap_v2] missing configuration field: {exc.args[0]}")

    return UniswapV2Config(
        router=router,
        lp_token=lp_token,
        token0=token0,
        token1=token1,
        slippage_bps=int(raw.get("slippage_bps", os.getenv("SWAP_SLIPPAGE_BPS", 100))),
    )


class UniswapV2Adapter(Adapter):
    """Adapter that routes liquidity to Uniswap v2 style LP pools."""

    def __init__(self, w3: Web3, config: Dict[str, object], signer, sender: str):
        self.w3 = w3
        self.signer = signer
        self.sender = Web3.to_checksum_address(sender)

        self.cfg = _load_config(config)
        self.router = _contract(w3, self.cfg.router, UNISWAP_V2_ROUTER_ABI)
        self.lp_token = _contract(w3, self.cfg.lp_token, ERC20_ABI)
        self.token0 = _contract(w3, self.cfg.token0, ERC20_ABI)
        self.token1 = _contract(w3, self.cfg.token1, ERC20_ABI)

    def deposit_all(self) -> Dict[str, object]:
        token0_balance = _balance(self.token0, self.sender)
        token1_balance = _balance(self.token1, self.sender)
        notes: list[str] = []

        if token0_balance == 0 or token1_balance == 0:
            missing = []
            if token0_balance == 0:
                missing.append(self.cfg.token0)
            if token1_balance == 0:
                missing.append(self.cfg.token1)
            return {"status": "no_assets", "missing": missing}

        amount0 = token0_balance
        amount1 = token1_balance

        slip = Decimal(1) - Decimal(self.cfg.slippage_bps) / Decimal(10_000)
        minA = math.floor(amount0 * slip)
        minB = math.floor(amount1 * slip)
        deadline = self.w3.eth.get_block("latest")["timestamp"] + 1800

        nonce = self.w3.eth.get_transaction_count(self.sender)
        approve0 = _approve_if_needed(self.w3, self.signer, self.token0, self.cfg.router, amount0, nonce=nonce)
        if approve0:
            notes.append(f"approve_token0:{approve0}")
            nonce += 1
        approve1 = _approve_if_needed(self.w3, self.signer, self.token1, self.cfg.router, amount1, nonce=nonce)
        if approve1:
            notes.append(f"approve_token1:{approve1}")
            nonce += 1

        tx = self.router.functions.addLiquidity(
            self.token0.address,
            self.token1.address,
            amount0,
            amount1,
            minA,
            minB,
            self.sender,
            deadline,
        ).build_transaction({"from": self.sender})
        add_liq_hash = _sign_and_send(self.w3, self.signer, tx, nonce=nonce)
        notes.append(f"addLiquidity:{add_liq_hash}")

        lp_balance = _balance(self.lp_token, self.sender)
        return {
            "status": "ok",
            "add_liquidity_tx": add_liq_hash,
            "lp_balance": lp_balance,
            "notes": notes,
            "assets_used": {"token0": amount0, "token1": amount1},
        }

    def withdraw_all(self) -> Dict[str, object]:
        lp_balance = _balance(self.lp_token, self.sender)
        notes: list[str] = []

        if lp_balance == 0:
            return {"status": "no_shares"}

        nonce = self.w3.eth.get_transaction_count(self.sender)
        approve_lp = _approve_if_needed(self.w3, self.signer, self.lp_token, self.cfg.router, lp_balance, nonce=nonce)
        if approve_lp:
            notes.append(f"approve_lp:{approve_lp}")
            nonce += 1

        slip = Decimal(1) - Decimal(self.cfg.slippage_bps) / Decimal(10_000)
        min0 = math.floor(lp_balance * slip / 2)
        min1 = math.floor(lp_balance * slip / 2)
        deadline = self.w3.eth.get_block("latest")["timestamp"] + 1800

        remove_tx = self.router.functions.removeLiquidity(
            self.token0.address,
            self.token1.address,
            lp_balance,
            min0,
            min1,
            self.sender,
            deadline,
        ).build_transaction({"from": self.sender})
        remove_hash = _sign_and_send(self.w3, self.signer, remove_tx, nonce=nonce)
        notes.append(f"removeLiquidity:{remove_hash}")

        return {
            "status": "ok",
            "remove_liquidity_tx": remove_hash,
            "notes": notes,
        }
