#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Adapter for Aerodrome Slipstream (concentrated liquidity pools, similar to Uniswap v3)."""

from __future__ import annotations

import os
from typing import Dict, Optional

from web3 import Web3
from web3.contract.contract import Contract

from abi_min import ERC20_ABI
from .base import Adapter

MAX_UINT256 = (1 << 256) - 1


# Aerodrome Slipstream uses a similar NFT position manager to Uniswap v3
SLIPSTREAM_NFT_MANAGER_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "token0", "type": "address"},
                    {"internalType": "address", "name": "token1", "type": "address"},
                    {"internalType": "int24", "name": "tickSpacing", "type": "int24"},
                    {"internalType": "int24", "name": "tickLower", "type": "int24"},
                    {"internalType": "int24", "name": "tickUpper", "type": "int24"},
                    {"internalType": "uint256", "name": "amount0Desired", "type": "uint256"},
                    {"internalType": "uint256", "name": "amount1Desired", "type": "uint256"},
                    {"internalType": "uint256", "name": "amount0Min", "type": "uint256"},
                    {"internalType": "uint256", "name": "amount1Min", "type": "uint256"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                    {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
                ],
                "internalType": "struct INonfungiblePositionManager.MintParams",
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "mint",
        "outputs": [
            {"internalType": "uint256", "name": "tokenId", "type": "uint256"},
            {"internalType": "uint128", "name": "liquidity", "type": "uint128"},
            {"internalType": "uint256", "name": "amount0", "type": "uint256"},
            {"internalType": "uint256", "name": "amount1", "type": "uint256"},
        ],
        "stateMutability": "payable",
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


class AerodromeSlipstreamAdapter(Adapter):
    """Adapter for Aerodrome Slipstream concentrated liquidity positions."""

    def __init__(self, w3: Web3, config: Dict[str, object], signer, sender: str):
        self.w3 = w3
        self.signer = signer
        self.sender = Web3.to_checksum_address(sender)

        try:
            self.nft_manager_address = str(config["nft_manager"])
            self.token0_address = str(config["token0"])
            self.token1_address = str(config["token1"])
            self.tick_spacing = int(config.get("tick_spacing", 200))
            self.tick_lower = int(config.get("tick_lower", -887220))
            self.tick_upper = int(config.get("tick_upper", 887220))
        except KeyError as exc:
            raise RuntimeError(f"[aerodrome_slipstream] missing configuration field: {exc.args[0]}")

        self.nft_manager = _contract(w3, self.nft_manager_address, SLIPSTREAM_NFT_MANAGER_ABI)
        self.token0 = _contract(w3, self.token0_address, ERC20_ABI)
        self.token1 = _contract(w3, self.token1_address, ERC20_ABI)
        self.slippage_bps = int(config.get("slippage_bps", 50))
        self.sqrt_price_x96 = int(config.get("sqrt_price_x96", 0))

    def deposit_all(self) -> Dict[str, object]:
        token0_balance = _balance(self.token0, self.sender)
        token1_balance = _balance(self.token1, self.sender)
        notes: list[str] = []

        if token0_balance == 0 or token1_balance == 0:
            missing = []
            if token0_balance == 0:
                missing.append(self.token0_address)
            if token1_balance == 0:
                missing.append(self.token1_address)
            return {"status": "no_assets", "missing": missing}

        nonce = self.w3.eth.get_transaction_count(self.sender)
        approve0 = _approve_if_needed(self.w3, self.signer, self.token0, self.nft_manager_address, token0_balance, nonce=nonce)
        if approve0:
            notes.append(f"approve_token0:{approve0}")
            nonce += 1
        approve1 = _approve_if_needed(self.w3, self.signer, self.token1, self.nft_manager_address, token1_balance, nonce=nonce)
        if approve1:
            notes.append(f"approve_token1:{approve1}")
            nonce += 1

        slip_factor = 1 - (self.slippage_bps / 10_000)
        min0 = int(token0_balance * slip_factor)
        min1 = int(token1_balance * slip_factor)
        deadline = self.w3.eth.get_block("latest")["timestamp"] + 1800

        mint_params = (
            self.token0.address,
            self.token1.address,
            self.tick_spacing,
            self.tick_lower,
            self.tick_upper,
            token0_balance,
            token1_balance,
            min0,
            min1,
            self.sender,
            deadline,
            self.sqrt_price_x96,
        )

        tx = self.nft_manager.functions.mint(mint_params).build_transaction({"from": self.sender})
        mint_hash = _sign_and_send(self.w3, self.signer, tx, nonce=nonce)
        notes.append(f"mint_position:{mint_hash}")

        return {
            "status": "ok",
            "mint_tx": mint_hash,
            "notes": notes,
            "assets_used": {"token0": token0_balance, "token1": token1_balance},
        }

    def withdraw_all(self) -> Dict[str, object]:
        # Note: Slipstream positions are NFTs, so withdrawing requires knowing the tokenId
        return {
            "status": "not_implemented",
            "reason": "Aerodrome Slipstream withdrawal requires NFT position management",
        }
