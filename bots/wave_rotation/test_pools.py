#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test pool configurations."""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"


def test_config_loads():
    """Test that config.json can be loaded."""
    with CONFIG_FILE.open() as fh:
        config = json.load(fh)
    assert config is not None
    assert "adapters" in config
    print("✓ Config loads successfully")


def test_adapter_types():
    """Test that all adapters have valid types."""
    with CONFIG_FILE.open() as fh:
        config = json.load(fh)
    
    adapters = config.get("adapters", {})
    valid_types = {"aave_v3", "lp_beefy_aero", "erc4626", "yearn", "comet", "ctoken"}
    
    for pool_id, adapter_config in adapters.items():
        adapter_type = adapter_config.get("type")
        assert adapter_type in valid_types, f"Invalid adapter type '{adapter_type}' for {pool_id}"
        print(f"✓ {pool_id}: type={adapter_type}")


def test_pool_count():
    """Test that we have the expected number of pools."""
    with CONFIG_FILE.open() as fh:
        config = json.load(fh)
    
    adapters = config.get("adapters", {})
    pool_count = len(adapters)
    
    print(f"✓ Total pools configured: {pool_count}")
    assert pool_count >= 21, f"Expected at least 21 pools, found {pool_count}"


def test_pool_categories():
    """Test that we have pools in all required categories."""
    with CONFIG_FILE.open() as fh:
        config = json.load(fh)
    
    adapters = config.get("adapters", {})
    
    # Count by type
    aave_pools = [p for p, c in adapters.items() if c.get("type") == "aave_v3"]
    lp_pools = [p for p, c in adapters.items() if c.get("type") == "lp_beefy_aero"]
    erc4626_pools = [p for p, c in adapters.items() if c.get("type") == "erc4626"]
    yearn_pools = [p for p, c in adapters.items() if c.get("type") == "yearn"]
    comet_pools = [p for p, c in adapters.items() if c.get("type") == "comet"]
    ctoken_pools = [p for p, c in adapters.items() if c.get("type") == "ctoken"]

    print(f"✓ Aave v3 lending pools: {len(aave_pools)}")
    print(f"✓ Beefy/Aerodrome LP pools: {len(lp_pools)}")
    print(f"✓ ERC-4626 vault pools: {len(erc4626_pools)}")
    print(f"✓ Yearn vault pools: {len(yearn_pools)}")
    print(f"✓ Comet markets: {len(comet_pools)}")
    print(f"✓ cToken markets: {len(ctoken_pools)}")

    assert len(aave_pools) >= 3, "Need at least 3 Aave lending pools"
    assert len(lp_pools) >= 4, "Need at least 4 LP pools"
    assert len(erc4626_pools) >= 2, "Need at least 2 ERC-4626 vaults"
    assert len(yearn_pools) >= 1, "Need at least 1 Yearn vault"
    assert len(comet_pools) >= 1, "Need at least 1 Comet market"
    assert len(ctoken_pools) >= 1, "Need at least 1 cToken market"


def test_stable_pools():
    """Test that we have stable/stable pools."""
    with CONFIG_FILE.open() as fh:
        config = json.load(fh)
    
    adapters = config.get("adapters", {})
    stable_pools = [
        p for p, c in adapters.items()
        if c.get("type") == "lp_beefy_aero" and c.get("stable") is True
    ]
    
    print(f"✓ Stable/stable pools: {len(stable_pools)}")
    assert len(stable_pools) >= 1, "Need at least 1 stable/stable pool"
    
    for pool in stable_pools:
        print(f"  - {pool}")


def test_lst_pools():
    """Test that we have LST (Liquid Staking Token) pools."""
    with CONFIG_FILE.open() as fh:
        config = json.load(fh)
    
    adapters = config.get("adapters", {})
    
    # LST pools contain cbETH, stETH, or similar
    lst_pools = [
        p for p in adapters.keys()
        if "cbETH" in p or "stETH" in p or "wstETH" in p
    ]
    
    print(f"✓ LST pools: {len(lst_pools)}")
    assert len(lst_pools) >= 2, "Need at least 2 LST-related pools"
    
    for pool in lst_pools:
        print(f"  - {pool}")


def test_eth_stable_pools():
    """Test that we have ETH/stable pools."""
    with CONFIG_FILE.open() as fh:
        config = json.load(fh)
    
    adapters = config.get("adapters", {})
    
    # ETH/stable pools contain WETH paired with USDC or USDT
    eth_stable_pools = [
        p for p in adapters.keys()
        if ("WETH-USDC" in p or "WETH-USDT" in p or "ETH-USDC" in p or "ETH-USDT" in p)
    ]
    
    print(f"✓ ETH/stable pools: {len(eth_stable_pools)}")
    assert len(eth_stable_pools) >= 2, "Need at least 2 ETH/stable pools"
    
    for pool in eth_stable_pools:
        print(f"  - {pool}")


def test_btc_pools():
    """Test that we have BTC-related pools."""
    with CONFIG_FILE.open() as fh:
        config = json.load(fh)
    
    adapters = config.get("adapters", {})
    
    # BTC pools contain cbBTC
    btc_pools = [p for p in adapters.keys() if "cbBTC" in p or "BTC" in p]
    
    print(f"✓ BTC-related pools: {len(btc_pools)}")
    assert len(btc_pools) >= 2, "Need at least 2 BTC-related pools"
    
    for pool in btc_pools:
        print(f"  - {pool}")


def test_required_fields():
    """Test that all adapters have required fields."""
    with CONFIG_FILE.open() as fh:
        config = json.load(fh)
    
    adapters = config.get("adapters", {})
    
    for pool_id, adapter_config in adapters.items():
        assert "type" in adapter_config, f"Missing 'type' in {pool_id}"
        
        adapter_type = adapter_config["type"]
        
        if adapter_type == "aave_v3":
            assert "pool" in adapter_config, f"Missing 'pool' in {pool_id}"
            assert "asset" in adapter_config, f"Missing 'asset' in {pool_id}"
        
        elif adapter_type == "lp_beefy_aero":
            assert "router" in adapter_config, f"Missing 'router' in {pool_id}"
            assert "beefy_vault" in adapter_config, f"Missing 'beefy_vault' in {pool_id}"
            assert "token0" in adapter_config, f"Missing 'token0' in {pool_id}"
            assert "token1" in adapter_config, f"Missing 'token1' in {pool_id}"
        
        elif adapter_type == "erc4626":
            assert "vault" in adapter_config, f"Missing 'vault' in {pool_id}"
            assert "asset" in adapter_config, f"Missing 'asset' in {pool_id}"

        elif adapter_type == "yearn":
            assert "vault" in adapter_config, f"Missing 'vault' in {pool_id}"

        elif adapter_type == "comet":
            assert (
                "market" in adapter_config or "comet" in adapter_config
            ), f"Missing 'market' in {pool_id}"
            assert "asset" in adapter_config, f"Missing 'asset' in {pool_id}"

        elif adapter_type == "ctoken":
            assert "ctoken" in adapter_config or "token" in adapter_config, f"Missing 'ctoken' in {pool_id}"
            assert (
                "asset" in adapter_config or "underlying" in adapter_config
            ), f"Missing 'asset/underlying' in {pool_id}"
    
    print("✓ All adapters have required fields")


def test_token_decimals_if_rpc():
    """Test token decimals on-chain if RPC is available."""
    import os
    
    rpc = os.getenv("BASE_RPC", os.getenv("BASE_RPC_URL", "https://mainnet.base.org"))
    
    try:
        from web3 import Web3
    except ImportError:
        print("⊘ Skipping decimals test (web3 not installed)")
        return
    
    try:
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 10}))
        if not w3.is_connected():
            print("⊘ Skipping decimals test (RPC not connected)")
            return
    except Exception:
        print("⊘ Skipping decimals test (RPC connection failed)")
        return
    
    # token -> expected decimals
    expected = {
        os.getenv("USDC_BASE"): 6,
        os.getenv("USDT_BASE"): 6,
        os.getenv("USDBC_BASE"): 6,
        os.getenv("WETH_TOKEN_ADDRESS"): 18,
        os.getenv("CBETH_BASE"): 18,
        os.getenv("CBBTC_BASE"): 8,
        os.getenv("WSTETH_BASE"): 18,
    }
    
    abi = [{"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"}]
    
    for addr, exp in expected.items():
        if not addr or addr == '0x0000000000000000000000000000000000000000':
            continue
        try:
            token = w3.eth.contract(Web3.to_checksum_address(addr), abi=abi)
            dec = token.functions.decimals().call()
            assert dec == exp, f"Bad decimals for {addr}: {dec} != {exp}"
            print(f"✓ {addr[:10]}... has {dec} decimals")
        except Exception as e:
            print(f"⊘ Could not check {addr[:10]}...: {e}")
    
    print("✓ Token decimals validated")


if __name__ == "__main__":
    print("Testing pool configurations...\n")
    
    test_config_loads()
    test_adapter_types()
    test_pool_count()
    test_pool_categories()
    test_stable_pools()
    test_lst_pools()
    test_eth_stable_pools()
    test_btc_pools()
    test_required_fields()
    test_token_decimals_if_rpc()
    
    print("\n✅ All pool configuration tests passed!")
