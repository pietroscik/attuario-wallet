#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Quick sanity checks for Base network token/vault addresses."""

from __future__ import annotations

import os
import sys
from typing import Optional

from web3 import HTTPProvider, Web3


ERC20_ABI = [
    {
        "name": "symbol",
        "outputs": [{"type": "string"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "name": "decimals",
        "outputs": [{"type": "uint8"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function",
    },
]

BEEFY_VAULT_ABI = [
    {
        "name": "want",
        "outputs": [{"type": "address"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "name": "strategy",
        "outputs": [{"type": "address"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function",
    },
]

WETH_GATEWAY_ABI = [
    {
        "name": "POOL",
        "outputs": [{"type": "address"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function",
    }
]


def _get_web3() -> Web3:
    rpc_url = (
        os.getenv("BASE_RPC")
        or os.getenv("RPC_URL")
        or "https://mainnet.base.org"
    )
    return Web3(HTTPProvider(rpc_url, request_kwargs={"timeout": 20}))


def _erc20_info(w3: Web3, address: str) -> tuple[str, int]:
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(address),
        abi=ERC20_ABI,
    )
    symbol = contract.functions.symbol().call()
    decimals = contract.functions.decimals().call()
    return symbol, int(decimals)


def _beefy_want(w3: Web3, address: str) -> tuple[str, Optional[str]]:
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(address),
        abi=BEEFY_VAULT_ABI,
    )
    want = contract.functions.want().call()
    try:
        strategy = contract.functions.strategy().call()
    except Exception:  # pragma: no cover - some vaults may not expose strategy()
        strategy = None
    return want, strategy


def _gateway_pool(w3: Web3, address: str) -> Optional[str]:
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(address),
        abi=WETH_GATEWAY_ABI,
    )
    try:
        return contract.functions.POOL().call()
    except Exception:
        return None


def main() -> int:
    w3 = _get_web3()

    checks: list[tuple[str, str]] = []
    for key in ("WETH_TOKEN_ADDRESS", "USDC_BASE", "CBBTC_BASE", "CLANKER_TOKEN_ADDRESS"):
        value = os.getenv(key)
        if value:
            checks.append((key, value))

    print("=== ERC20 TOKENS ===")
    for key, address in checks:
        symbol, decimals = _erc20_info(w3, address)
        print(f"{key:<22} {address} -> symbol={symbol}, decimals={decimals}")

    beefy_vault = os.getenv("BEEFY_USDC_CBBTC_VAULT")
    if beefy_vault:
        want, strategy = _beefy_want(w3, beefy_vault)
        print("\n=== BEEFY VAULT (USDC/cbBTC) ===")
        print(f"vault:    {beefy_vault}")
        print(f"want():   {want}")
        if strategy:
            print(f"strategy:{strategy}")

    gateway = os.getenv("AAVE_WETH_GATEWAY_8453")
    pool_expected = os.getenv("AAVE_POOL_ADDRESS_8453")
    if gateway:
        actual = _gateway_pool(w3, gateway)
        print("\n=== AAVE WETH GATEWAY ===")
        print(f"gateway:  {gateway}")
        print(f"POOL():   {actual}")
        if pool_expected:
            print(f"expected: {pool_expected}")
            if actual and actual.lower() != pool_expected.lower():
                print("!! WARNING: gateway POOL() does not match expected pool address")

    print("\nValidation complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
