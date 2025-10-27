#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sanity check for explicit adapters defined in bots/wave_rotation/config.json.

The script resolves environment variables in the adapters section and performs
lightweight on-chain introspection (asset address, decimals, etc.) without
moving funds.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from web3 import HTTPProvider, Web3

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None


CONFIG_PATH = Path("bots/wave_rotation/config.json")

ERC20_META_ABI = [
    {
        "name": "decimals",
        "outputs": [{"type": "uint8"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "name": "symbol",
        "outputs": [{"type": "string"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function",
    },
]

ERC4626_META_ABI = [
    {
        "name": "asset",
        "outputs": [{"type": "address"}],
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


def expand_env(value):
    if isinstance(value, str):
        resolved = os.path.expandvars(value)
        if resolved.startswith("${") and resolved.endswith("}"):
            return ""
        if resolved.startswith("$") and "{" not in resolved:
            return ""
        return resolved
    if isinstance(value, dict):
        return {k: expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env(v) for v in value]
    return value


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_PATH}")
    data = json.loads(CONFIG_PATH.read_text())
    adapters = data.get("adapters", {}) or {}
    return {k: expand_env(v) for k, v in adapters.items()}


def get_web3() -> Web3:
    rpc_url = (
        os.getenv("RPC_URL")
        or os.getenv("BASE_RPC")
        or "https://mainnet.base.org"
    )
    return Web3(HTTPProvider(rpc_url, request_kwargs={"timeout": 20}))


def check_erc4626(w3: Web3, label: str, cfg: dict) -> bool:
    ok = True
    vault_addr = cfg.get("vault")
    asset_addr = cfg.get("asset")
    if not vault_addr or not asset_addr:
        print(f"  !! Missing vault/asset for {label}")
        return False

    vault = w3.eth.contract(address=Web3.to_checksum_address(vault_addr), abi=ERC4626_META_ABI)
    asset = w3.eth.contract(address=Web3.to_checksum_address(asset_addr), abi=ERC20_META_ABI)

    try:
        vault_asset = vault.functions.asset().call()
        vault_decimals = vault.functions.decimals().call()
    except Exception as exc:
        print(f"  !! Unable to read vault metadata: {exc}")
        return False

    try:
        symbol = asset.functions.symbol().call()
        decimals = asset.functions.decimals().call()
    except Exception as exc:
        print(f"  !! Unable to read asset metadata: {exc}")
        return False

    print(f"  vault.asset() = {vault_asset}")
    print(f"  cfg.asset     = {asset_addr}")
    print(f"  token {symbol} decimals={decimals} | vault.decimals={vault_decimals}")

    if vault_asset.lower() != asset_addr.lower():
        print("  !! Mismatch between vault.asset() and configured asset")
        ok = False
    if "decimals" in cfg and int(cfg["decimals"]) != vault_decimals:
        print("  !! Configured decimals differ from vault.decimals")
        ok = False
    if decimals != vault_decimals:
        print("  !! Asset/token decimals differ from vault.decimals")
        ok = False
    return ok


def check_aave(w3: Web3, label: str, cfg: dict) -> bool:
    pool = cfg.get("pool")
    asset = cfg.get("asset")
    if not pool or not asset:
        print(f"  !! Missing pool/asset for {label}")
        return False

    try:
        checksum_pool = Web3.to_checksum_address(pool)
        checksum_asset = Web3.to_checksum_address(asset)
    except Exception as exc:
        print(f"  !! Invalid address: {exc}")
        return False

    print(f"  pool={checksum_pool}")
    print(f"  asset={checksum_asset}")
    print(f"  chainId={w3.eth.chain_id}")
    gateway = cfg.get("weth_gateway")
    if gateway:
        try:
            print(f"  weth_gateway={Web3.to_checksum_address(gateway)}")
        except Exception as exc:
            print(f"  !! Invalid weth_gateway: {exc}")
            return False
    return True


def main() -> int:
    if load_dotenv:
        load_dotenv()
    adapters = load_config()
    if not adapters:
        print("No explicit adapters configured.")
        return 0

    w3 = get_web3()
    ok = True

    for key, cfg in adapters.items():
        adapter_type = str(cfg.get("type", "")).lower()
        print(f"\n[{key}] type={adapter_type}")
        if adapter_type == "erc4626":
            ok &= check_erc4626(w3, key, cfg)
        elif adapter_type == "aave_v3":
            ok &= check_aave(w3, key, cfg)
        elif adapter_type == "lp_beefy_aero":
            required = [cfg.get("router"), cfg.get("beefy_vault"), cfg.get("token0"), cfg.get("token1")]
            if any(not value for value in required):
                print("  !! Missing router/beefy_vault/token0/token1")
                ok = False
            else:
                print(f"  router={cfg['router']}")
                print(f"  beefy_vault={cfg['beefy_vault']}")
                print(f"  token0={cfg['token0']} | token1={cfg['token1']}")
                print(f"  stable={cfg.get('stable', False)} | slippage_bps={cfg.get('slippage_bps', 0)}")
        else:
            print("  (no checker for this adapter type)")

    print("\nResult:", "OK" if ok else "ISSUES FOUND")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
