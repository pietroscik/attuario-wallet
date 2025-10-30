#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Multi-Strategy Demonstration Script

Simulates multi-strategy allocation with a mock wallet containing:
- ETH
- WETH
- USDC
- EURC
- ANON

Shows how the optimizer would allocate these assets across available pools.
"""

import os
import sys
from pathlib import Path

# Setup test environment
os.environ["MULTI_STRATEGY_ENABLED"] = "true"
os.environ["STRATEGY_BUFFER_PERCENT"] = "5.0"
os.environ["MIN_INVESTMENT_PER_POOL"] = "0.01"
os.environ["MAX_POOLS_PER_ASSET"] = "3"
os.environ["PORTFOLIO_DRY_RUN"] = "true"
os.environ["ETH_PRICE_USD"] = "3000"

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from multi_strategy import (
    execute_multi_strategy,
    print_allocation_summary,
    MultiStrategyConfig,
)


def create_mock_wallet():
    """Create a mock wallet with multiple assets."""
    return {
        "native": 0.5,  # 0.5 ETH
        "0x4200000000000000000000000000000000000006": 2.0,  # 2.0 WETH
        "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": 5000.0,  # 5000 USDC
        "0x60a3e35cc302bfa44cb288bc5a4f316fdb1adb42": 3000.0,  # 3000 EURC
        # ANON token (if configured)
        "0x0db510e79909666d6dec7f5e49370838c16d950f": 100.0,  # 100 ANON (example)
    }


def create_token_labels():
    """Create token labels for display."""
    return {
        "native": "ETH",
        "0x4200000000000000000000000000000000000006": "WETH",
        "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": "USDC",
        "0x60a3e35cc302bfa44cb288bc5a4f316fdb1adb42": "EURC",
        "0x0db510e79909666d6dec7f5e49370838c16d950f": "ANON",
    }


def create_mock_config():
    """Create a mock configuration with adapters."""
    return {
        "chains": ["base"],
        "sources": {
            "defillama": False,  # Disable to avoid external calls
        },
        "adapters": {
            # WETH adapters
            "pool:base:aave-v3:WETH": {
                "type": "aave_v3",
                "pool": "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
                "asset": "0x4200000000000000000000000000000000000006",
            },
            "pool:base:morpho:WETH": {
                "type": "erc4626",
                "vault": "0x38989BBA00BDF8181F4082995b3DEAe96163aC5D",
                "asset": "0x4200000000000000000000000000000000000006",
            },
            # USDC adapters
            "pool:base:aave-v3:USDC": {
                "type": "aave_v3",
                "pool": "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            },
            "pool:base:morpho:USDC": {
                "type": "erc4626",
                "vault": "0xef417a2512C5a41f69AE4e021648b69a7CdE5D03",
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            },
            "pool:base:comet:USDC": {
                "type": "comet",
                "market": "0x46e6b214b524310239732D51387075E0e70970bf",
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            },
            # EURC adapter
            "pool:base:beefy:WETH-EURC": {
                "type": "lp_beefy_aero",
                "router": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
                "beefy_vault": "0xBEEFY_VAULT_ADDRESS",
                "token0": "0x4200000000000000000000000000000000000006",
                "token1": "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42",
            },
            # ANON adapter
            "pool:base:beefy:ANON-WETH": {
                "type": "lp_beefy_aero",
                "router": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
                "beefy_vault": "0xBEEFY_ANON_VAULT",
                "token0": "0x0db510e79909666d6dec7f5e49370838c16d950f",
                "token1": "0x4200000000000000000000000000000000000006",
            },
        },
    }


def inject_mock_pools():
    """Inject mock pool data into the system."""
    # This would normally come from DeFiLlama or other APIs
    # For demonstration, we'll create synthetic pools
    return [
        {
            "pool_id": "base:aave-v3:WETH",
            "name": "Aave V3 WETH",
            "chain": "base",
            "apy": 0.035,  # 3.5% APY
            "tvl_usd": 50000000,
            "risk_score": 0.1,
            "fee_pct": 0.0,
        },
        {
            "pool_id": "base:morpho:WETH",
            "name": "Morpho WETH Vault",
            "chain": "base",
            "apy": 0.045,  # 4.5% APY
            "tvl_usd": 30000000,
            "risk_score": 0.15,
            "fee_pct": 0.001,
        },
        {
            "pool_id": "base:aave-v3:USDC",
            "name": "Aave V3 USDC",
            "chain": "base",
            "apy": 0.055,  # 5.5% APY
            "tvl_usd": 100000000,
            "risk_score": 0.08,
            "fee_pct": 0.0,
        },
        {
            "pool_id": "base:morpho:USDC",
            "name": "Morpho USDC Vault",
            "chain": "base",
            "apy": 0.072,  # 7.2% APY
            "tvl_usd": 80000000,
            "risk_score": 0.12,
            "fee_pct": 0.001,
        },
        {
            "pool_id": "base:comet:USDC",
            "name": "Compound V3 USDC",
            "chain": "base",
            "apy": 0.062,  # 6.2% APY
            "tvl_usd": 60000000,
            "risk_score": 0.10,
            "fee_pct": 0.0005,
        },
        {
            "pool_id": "base:beefy:WETH-EURC",
            "name": "Beefy WETH-EURC LP",
            "chain": "base",
            "apy": 0.085,  # 8.5% APY (LP typically higher)
            "tvl_usd": 5000000,
            "risk_score": 0.25,
            "fee_pct": 0.002,
        },
        {
            "pool_id": "base:beefy:ANON-WETH",
            "name": "Beefy ANON-WETH LP",
            "chain": "base",
            "apy": 0.150,  # 15% APY (volatile token, higher reward)
            "tvl_usd": 1000000,
            "risk_score": 0.60,
            "fee_pct": 0.003,
        },
    ]


def main():
    """Run the demonstration."""
    print("=" * 70)
    print("MULTI-STRATEGY OPTIMIZER DEMONSTRATION")
    print("=" * 70)
    
    # Load configuration
    config = MultiStrategyConfig.load()
    print(f"\n📋 Configuration:")
    print(f"  • Multi-Strategy: {'ENABLED' if config.enabled else 'DISABLED'}")
    print(f"  • Buffer Reserve: {config.buffer_percent}%")
    print(f"  • Min Investment: {config.min_investment_per_pool}")
    print(f"  • Max Pools per Asset: {config.max_pools_per_asset}")
    
    # Create mock wallet
    wallet = create_mock_wallet()
    labels = create_token_labels()
    
    print(f"\n💼 Wallet Contents:")
    eth_price = float(os.getenv("ETH_PRICE_USD", "3000"))
    total_usd = 0.0
    
    for addr, balance in wallet.items():
        label = labels.get(addr, addr[:10])
        if addr == "native" or "weth" in label.lower():
            usd_value = balance * eth_price
        else:
            usd_value = balance  # Assuming stablecoins ~$1
        total_usd += usd_value
        print(f"  • {label}: {balance:.6f} (≈${usd_value:.2f})")
    
    print(f"\n  💰 Total Portfolio Value: ${total_usd:.2f}")
    print(f"  🛡️  Reserved (Buffer): ${total_usd * 0.05:.2f} ({config.buffer_percent}%)")
    print(f"  📊 Allocatable: ${total_usd * 0.95:.2f}")
    
    # Mock the pool fetching (in real use, this would call APIs)
    print(f"\n🔍 Scanning Available Pools...")
    mock_pools = inject_mock_pools()
    print(f"  Found {len(mock_pools)} compatible pools")
    
    # Display pools
    print(f"\n📊 Available Pools:")
    for pool in mock_pools:
        print(f"  • {pool['name']}")
        print(f"    APY: {pool['apy']:.2%} | TVL: ${pool['tvl_usd']:,.0f} | Risk: {pool['risk_score']:.2f}")
    
    # Simulate allocation by manually calling matching and optimization
    from multi_strategy import (
        match_pools_to_assets,
        optimize_allocations,
        execute_allocations,
        save_allocation_state,
    )
    from pathlib import Path
    
    config_dict = create_mock_config()
    
    print(f"\n🎯 Matching Assets to Pools...")
    matches = match_pools_to_assets(mock_pools, wallet, config_dict, config)
    
    print(f"  Matched {len(matches)} assets:")
    for asset_addr, pool_list in matches.items():
        label = labels.get(asset_addr, asset_addr[:10])
        print(f"  • {label}: {len(pool_list)} compatible pool(s)")
    
    print(f"\n⚡ Optimizing Allocations...")
    allocations = optimize_allocations(matches, wallet, labels, config, eth_price)
    
    print(f"  Generated {len(allocations)} allocation plans")
    
    print(f"\n🚀 Executing Allocations (DRY RUN)...")
    results = execute_allocations(allocations, config_dict, None, None, dry_run=True)
    
    # Print summary
    print_allocation_summary(allocations, results)
    
    # Save state
    state_file = Path(__file__).parent / "demo_multi_strategy_state.json"
    save_allocation_state(allocations, results, state_file)
    print(f"\n💾 State saved to: {state_file}")
    
    # Calculate statistics
    if allocations:
        total_allocated_usd = sum(a.allocation_usd for a in allocations)
        avg_apy = sum(a.pool_apy for a in allocations) / len(allocations)
        avg_score = sum(a.pool_score for a in allocations) / len(allocations)
        
        print(f"\n📈 Allocation Statistics:")
        print(f"  • Total Allocated: ${total_allocated_usd:.2f}")
        print(f"  • Coverage: {(total_allocated_usd / total_usd * 100):.1f}%")
        print(f"  • Average APY: {avg_apy:.2%}")
        print(f"  • Average Score: {avg_score:.6f}")
        print(f"  • Assets Diversified: {len(allocations)}")
    
    print("\n" + "=" * 70)
    print("✅ DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("\nTo enable in production:")
    print("  1. Set MULTI_STRATEGY_ENABLED=true in .env")
    print("  2. Configure STRATEGY_BUFFER_PERCENT (default: 5%)")
    print("  3. Set PORTFOLIO_DRY_RUN=false for live execution")
    print("  4. Ensure TREASURY_AUTOMATION_ENABLED=true for treasury integration")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
