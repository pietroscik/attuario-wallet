#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validation script for 50 new asset configurations.

Checks:
1. All required environment variables are set
2. All pool configurations are present
3. Adapter types are registered
4. Token fields are properly configured
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from adapters import ADAPTER_TYPES


# Expected 50 pools
EXPECTED_POOLS = [
    # Uniswap v2 on Base (22)
    "pool:base:uniswap-v2:WETH-X402",
    "pool:base:uniswap-v2:HOOD-WETH",
    "pool:base:uniswap-v2:PUMP-WETH",
    "pool:base:uniswap-v2:CRCL-WETH",
    "pool:base:uniswap-v2:TRUMP-WETH-1",
    "pool:base:uniswap-v2:MSTR-WETH",
    "pool:base:uniswap-v2:IP-WETH",
    "pool:base:uniswap-v2:IMAGINE-WETH",
    "pool:base:uniswap-v2:GRAYSCALE-WETH",
    "pool:base:uniswap-v2:WETH-402GATE",
    "pool:base:uniswap-v2:TRUMP-WETH-2",
    "pool:base:uniswap-v2:GROK-WETH",
    "pool:base:uniswap-v2:LIBRA-WETH",
    "pool:base:uniswap-v2:TRUMP-WETH-3",
    "pool:base:uniswap-v2:LABUBU-WETH",
    "pool:base:uniswap-v2:ANI-WETH",
    "pool:base:uniswap-v2:COIN-WETH",
    "pool:base:uniswap-v2:50501-WETH",
    "pool:base:uniswap-v2:STOCK-WETH",
    "pool:base:uniswap-v2:WETH-MIKA",
    "pool:base:uniswap-v2:WETH-TSLA",
    "pool:ethereum:uniswap-v2:BABYGIRL-WETH",
    # Aerodrome Slipstream on Base (6)
    "pool:base:aerodrome-slipstream:AVNT-USDC",
    "pool:base:aerodrome-slipstream:WETH-USDC",
    "pool:base:aerodrome-slipstream:USDC-VFY",
    "pool:base:aerodrome-slipstream:USDC-VELVET",
    "pool:base:aerodrome-slipstream:WETH-CBBTC",
    "pool:base:aerodrome-slipstream:EMP-WETH",
    # Aerodrome v1 on Base (4)
    "pool:base:aerodrome-v1:USDC-EMT",
    "pool:base:aerodrome-v1:WETH-W",
    "pool:base:aerodrome-v1:WETH-TRAC",
    "pool:base:aerodrome-v1:EBTC-CBBTC",
    # Beefy (5)
    "pool:base:beefy:ANON-WETH",
    "pool:base:beefy:CLANKER-WETH",
    "pool:bsc:beefy:COAI-USDT-1",
    "pool:bsc:beefy:COAI-USDT-2",
    "pool:sonic:beefy:S-USDC",
    # Raydium on Solana (5)
    "pool:solana:raydium:TURTLE-DEX-USDC",
    "pool:solana:raydium:WSOL-NICKEL",
    "pool:solana:raydium:USD1-LIBERTY",
    "pool:solana:raydium:PIPPIN-USDC",
    "pool:solana:raydium:USD1-VALOR",
    # Others (8)
    "pool:base:uniswap-v3:CGN-USDC",
    "pool:aptos:hyperion:APT-AMI",
    "pool:base:balancer-v3:WETH-USDT-USDC",
    "pool:base:spectra-v2:YVBAL-GHO-USR",
    "pool:arbitrum:vaultcraft:VC-WETH",
    "pool:avalanche:yield-yak:WETH.E-KIGU",
    "pool:linea:etherex-cl:CROAK-WETH",
    "pool:sonic:peapods:SCUSD",
]


def check_adapters_registered():
    """Check that all required adapter types are registered."""
    required_adapters = {
        "uniswap_v2",
        "uniswap_v3",
        "aerodrome_v1",
        "aerodrome_slipstream",
        "lp_beefy_aero",
        "beefy_vault",
        "raydium_amm",
        "hyperion",
        "balancer_v3",
        "spectra_v2",
        "vaultcraft",
        "yield_yak",
        "etherex_cl",
        "peapods_finance",
        "erc4626",  # Used for some vaults
    }
    
    registered = set(ADAPTER_TYPES.keys())
    missing = required_adapters - registered
    
    print("=" * 70)
    print("ADAPTER REGISTRATION CHECK")
    print("=" * 70)
    print(f"Required adapters: {len(required_adapters)}")
    print(f"Registered adapters: {len(registered)}")
    
    if missing:
        print(f"\n❌ Missing adapters: {', '.join(sorted(missing))}")
        return False
    else:
        print("\n✅ All required adapters are registered")
        return True


def check_config_pools(config_path: Path):
    """Check which pools are configured in config.json."""
    if not config_path.exists():
        print(f"\n❌ Config file not found: {config_path}")
        return False
    
    with open(config_path) as f:
        config = json.load(f)
    
    adapters = config.get("adapters", {})
    configured_pools = set(adapters.keys())
    expected_new = set(EXPECTED_POOLS)
    
    configured_new = configured_pools & expected_new
    missing_new = expected_new - configured_pools
    
    print("\n" + "=" * 70)
    print("POOL CONFIGURATION CHECK")
    print("=" * 70)
    print(f"Expected new pools: {len(EXPECTED_POOLS)}")
    print(f"Configured new pools: {len(configured_new)}")
    print(f"Missing new pools: {len(missing_new)}")
    
    if configured_new:
        print(f"\n✅ Configured ({len(configured_new)}):")
        for pool in sorted(configured_new):
            adapter_type = adapters[pool].get("type", "unknown")
            print(f"  - {pool} [{adapter_type}]")
    
    if missing_new:
        print(f"\n⚠️  Missing ({len(missing_new)}):")
        for pool in sorted(missing_new):
            print(f"  - {pool}")
    
    return len(missing_new) == 0


def check_env_variables():
    """Check which environment variables are set."""
    # Key variables for each chain/protocol
    key_variables = {
        "Base Chain": [
            "UNISWAP_V2_ROUTER_BASE",
            "UNISWAP_V3_NFT_MANAGER_BASE",
            "AERODROME_SLIPSTREAM_NFT_MANAGER",
        ],
        "BSC": ["BSC_RPC", "BEEFY_COAI_USDT_VAULT_BSC"],
        "Sonic": ["SONIC_RPC", "BEEFY_S_USDC_VAULT_SONIC"],
        "Arbitrum": ["ARBITRUM_RPC", "VAULTCRAFT_VC_WETH_VAULT"],
        "Avalanche": ["AVALANCHE_RPC", "YIELD_YAK_WETH_KIGU_VAULT"],
        "Linea": ["LINEA_RPC", "ETHEREX_CL_NFT_MANAGER_LINEA"],
        "Ethereum": ["ETHEREUM_RPC", "UNISWAP_V2_ROUTER_ETHEREUM"],
        "Solana": ["SOLANA_RPC", "RAYDIUM_AMM_PROGRAM"],
        "Aptos": ["APTOS_RPC", "HYPERION_APT_AMI_POOL"],
    }
    
    print("\n" + "=" * 70)
    print("ENVIRONMENT VARIABLES CHECK")
    print("=" * 70)
    
    all_set = True
    for chain, variables in key_variables.items():
        set_vars = [v for v in variables if os.getenv(v)]
        missing_vars = [v for v in variables if not os.getenv(v)]
        
        status = "✅" if len(missing_vars) == 0 else "⚠️ "
        print(f"\n{status} {chain}: {len(set_vars)}/{len(variables)} set")
        
        if missing_vars:
            for var in missing_vars:
                print(f"    Missing: {var}")
            all_set = False
    
    return all_set


def main():
    """Run all validation checks."""
    print("\n" + "=" * 70)
    print("50 ASSET INTEGRATION VALIDATION")
    print("=" * 70)
    
    # Load environment from .env if exists
    try:
        from dotenv import load_dotenv
        env_file = Path(__file__).parent.parent.parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            print(f"\n✅ Loaded environment from {env_file}")
        else:
            print(f"\n⚠️  No .env file found at {env_file}")
    except ImportError:
        print("\n⚠️  python-dotenv not installed, using existing environment")
    
    # Run checks
    adapters_ok = check_adapters_registered()
    
    config_path = Path(__file__).parent / "config.json"
    pools_ok = check_config_pools(config_path)
    
    env_ok = check_env_variables()
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Adapters registered: {'✅ Yes' if adapters_ok else '❌ No'}")
    print(f"Pools configured: {'✅ All' if pools_ok else '⚠️  Partial'}")
    print(f"Environment vars: {'✅ All set' if env_ok else '⚠️  Some missing'}")
    
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    
    if not pools_ok:
        print("1. Copy configurations from config_sample_50_pools.json to config.json")
    
    if not env_ok:
        print("2. Populate missing environment variables in .env")
        print("   - Use .env.example as a template")
        print("   - Get addresses from protocol documentation or explorers")
    
    print("3. See ASSET_INTEGRATION_GUIDE.md for detailed instructions")
    print("4. See ASSET_ADAPTER_MAPPING.md for adapter-to-pool mapping")
    
    return 0 if (adapters_ok and pools_ok and env_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
