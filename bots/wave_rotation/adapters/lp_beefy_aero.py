#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Adapter for Beefy vaults backed by Aerodrome/Velodrome LPs."""

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


ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"},
            {"internalType": "bool", "name": "stable", "type": "bool"},
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
            {"internalType": "bool", "name": "stable", "type": "bool"},
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
class BeefyAerodromeConfig:
    router: str
    beefy_vault: str
    token0: str
    token1: str
    stable: bool
    weth: str
    slippage_bps: int


def _load_config(raw: Dict[str, object]) -> BeefyAerodromeConfig:
    try:
        router = raw["router"]
        beefy = raw["beefy_vault"]
        token0 = raw["token0"]
        token1 = raw["token1"]
    except KeyError as exc:
        raise RuntimeError(f"[lp_beefy_aero] missing configuration field: {exc.args[0]}")

    return BeefyAerodromeConfig(
        router=router,
        beefy_vault=beefy,
        token0=token0,
        token1=token1,
        stable=bool(raw.get("stable", False)),
        weth=str(raw.get("weth") or "0x4200000000000000000000000000000000000006"),
        slippage_bps=int(raw.get("slippage_bps", os.getenv("SWAP_SLIPPAGE_BPS", 100))),
    )


class LpBeefyAerodromeAdapter(Adapter):
    """Adapter that routes liquidity to Beefy vaults built on Aerodrome LP tokens."""

    def __init__(self, w3: Web3, config: Dict[str, object], signer, sender: str):
        self.w3 = w3
        self.signer = signer
        self.sender = Web3.to_checksum_address(sender)

        self.cfg = _load_config(config)
        self.router = _contract(w3, self.cfg.router, ROUTER_ABI)
        self.vault = _contract(w3, self.cfg.beefy_vault, BEEFY_VAULT_ABI)
        self.token0 = _contract(w3, self.cfg.token0, ERC20_ABI)
        self.token1 = _contract(w3, self.cfg.token1, ERC20_ABI)
        self.weth = _contract(w3, self.cfg.weth, ERC20_ABI)
        self.want = _contract(w3, self.vault.functions.want().call(), ERC20_ABI)

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
        amountA = min(amount0, amount1)
        amountB = min(amount0, amount1)

        slip = Decimal(1) - Decimal(self.cfg.slippage_bps) / Decimal(10_000)
        minA = math.floor(amountA * slip)
        minB = math.floor(amountB * slip)
        deadline = self.w3.eth.get_block("latest")["timestamp"] + 1800

        nonce = self.w3.eth.get_transaction_count(self.sender)
        approve0 = _approve_if_needed(self.w3, self.signer, self.token0, self.cfg.router, amountA, nonce=nonce)
        if approve0:
            notes.append(f"approve_token0:{approve0}")
            nonce += 1
        approve1 = _approve_if_needed(self.w3, self.signer, self.token1, self.cfg.router, amountB, nonce=nonce)
        if approve1:
            notes.append(f"approve_token1:{approve1}")
            nonce += 1

        tx = self.router.functions.addLiquidity(
            self.token0.address,
            self.token1.address,
            self.cfg.stable,
            amountA,
            amountB,
            minA,
            minB,
            self.sender,
            deadline,
        ).build_transaction({"from": self.sender})
        add_liq_hash = _sign_and_send(self.w3, self.signer, tx, nonce=nonce)
        notes.append(f"addLiquidity:{add_liq_hash}")
        nonce += 1

        lp_balance = _balance(self.want, self.sender)
        if lp_balance == 0:
            return {"status": "mint_failed", "notes": notes}

        approve_lp = _approve_if_needed(self.w3, self.signer, self.want, self.cfg.beefy_vault, lp_balance, nonce=nonce)
        if approve_lp:
            notes.append(f"approve_lp:{approve_lp}")
            nonce += 1

        deposit_tx = self.vault.functions.deposit(lp_balance).build_transaction({"from": self.sender})
        deposit_hash = _sign_and_send(self.w3, self.signer, deposit_tx, nonce=nonce)
        notes.append(f"beefy.deposit:{deposit_hash}")

        return {
            "status": "ok",
            "deposit_tx": deposit_hash,
            "add_liquidity_tx": add_liq_hash,
            "notes": notes,
            "assets_used": {"token0": amountA, "token1": amountB},
        }

    def withdraw_all(self) -> Dict[str, object]:
        shares = self.vault.functions.balanceOf(self.sender).call()
        notes: list[str] = []

        if shares == 0:
            return {"status": "no_shares"}

        nonce = self.w3.eth.get_transaction_count(self.sender)
        withdraw_tx = self.vault.functions.withdraw(shares).build_transaction({"from": self.sender})
        withdraw_hash = _sign_and_send(self.w3, self.signer, withdraw_tx, nonce=nonce)
        notes.append(f"beefy.withdraw:{withdraw_hash}")
        nonce += 1

        lp_balance = _balance(self.want, self.sender)
        if lp_balance == 0:
            return {"status": "lp_unavailable", "notes": notes}

        approve_lp = _approve_if_needed(self.w3, self.signer, self.want, self.cfg.router, lp_balance, nonce=nonce)
        if approve_lp:
            notes.append(f"approve_lp_router:{approve_lp}")
            nonce += 1

        slip = Decimal(1) - Decimal(self.cfg.slippage_bps) / Decimal(10_000)
        min0 = math.floor(lp_balance * slip / 2)
        min1 = math.floor(lp_balance * slip / 2)
        deadline = self.w3.eth.get_block("latest")["timestamp"] + 1800

        remove_tx = self.router.functions.removeLiquidity(
            self.token0.address,
            self.token1.address,
            self.cfg.stable,
            lp_balance,
            min0,
            min1,
            self.sender,
            deadline,
        ).build_transaction({"from": self.sender})
        remove_hash = _sign_and_send(self.w3, self.signer, remove_tx, nonce=nonce)
        notes.append(f"removeLiquidity:{remove_hash}")
        notes.append("swap_back_pending: complete leg unwinds via 0x/uniswap as needed")

        return {
            "status": "ok",
            "withdraw_tx": withdraw_hash,
            "remove_liquidity_tx": remove_hash,
            "notes": notes,
        }
