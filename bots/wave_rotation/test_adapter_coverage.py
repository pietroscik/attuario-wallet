#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test adapter coverage and configuration."""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


def test_adapter_types():
    """Test that all adapter types are properly configured."""
    with CONFIG_PATH.open() as f:
        config = json.load(f)
    
    adapters = config.get("adapters", {})
    
    # Expected adapter types
    expected_types = {
        "aave_v3",
        "lp_beefy_aero",
        "erc4626",
        "yearn",
        "comet",
        "ctoken",
    }
    
    found_types = set()
    for pool_id, adapter_config in adapters.items():
        adapter_type = adapter_config.get("type")
        if adapter_type:
            found_types.add(adapter_type)
    
    missing_types = expected_types - found_types
    if missing_types:
        print(f"❌ Missing adapter types: {missing_types}")
        return False
    
    print(f"✅ All expected adapter types present: {sorted(found_types)}")
    return True


def test_adapter_count():
    """Test that we have expanded adapter coverage."""
    with CONFIG_PATH.open() as f:
        config = json.load(f)
    
    adapters = config.get("adapters", {})
    total_adapters = len(adapters)
    
    # We should have at least 20 adapters configured
    if total_adapters < 20:
        print(f"❌ Too few adapters: {total_adapters} (expected >= 20)")
        return False
    
    print(f"✅ Good adapter coverage: {total_adapters} pools configured")
    return True


def test_protocol_diversity():
    """Test that we cover multiple protocols."""
    with CONFIG_PATH.open() as f:
        config = json.load(f)
    
    adapters = config.get("adapters", {})
    
    # Count by adapter type
    type_counts = {}
    for pool_id, adapter_config in adapters.items():
        adapter_type = adapter_config.get("type", "unknown")
        type_counts[adapter_type] = type_counts.get(adapter_type, 0) + 1
    
    print("\n📊 Protocol Distribution:")
    for adapter_type, count in sorted(type_counts.items()):
        print(f"  {adapter_type}: {count} pools")
    
    # We should have at least 3 pools for major protocols
    critical_protocols = ["aave_v3", "erc4626"]
    for protocol in critical_protocols:
        if type_counts.get(protocol, 0) < 3:
            print(f"❌ Insufficient coverage for {protocol}")
            return False
    
    print("✅ Good protocol diversity")
    return True


def test_asset_diversity():
    """Test that we support multiple assets."""
    with CONFIG_PATH.open() as f:
        config = json.load(f)
    
    adapters = config.get("adapters", {})
    
    # Extract assets from pool IDs
    assets = set()
    for pool_id in adapters.keys():
        # Pool ID format: pool:base:protocol:ASSET or pool:base:protocol:ASSET1-ASSET2
        parts = pool_id.split(":")
        if len(parts) >= 4:
            asset_part = parts[3]
            # Handle LP pairs
            if "-" in asset_part:
                for asset in asset_part.split("-"):
                    assets.add(asset.upper())
            else:
                assets.add(asset_part.upper())
    
    print(f"\n💰 Assets covered: {sorted(assets)}")
    
    # We should support key assets
    required_assets = {"USDC", "WETH"}
    missing_assets = required_assets - assets
    if missing_assets:
        print(f"❌ Missing required assets: {missing_assets}")
        return False
    
    if len(assets) < 5:
        print(f"❌ Too few assets: {len(assets)} (expected >= 5)")
        return False
    
    print(f"✅ Good asset diversity: {len(assets)} unique assets")
    return True


def test_chain_coverage():
    """Test that we focus on Base chain."""
    with CONFIG_PATH.open() as f:
        config = json.load(f)
    
    adapters = config.get("adapters", {})
    chains = config.get("chains", [])
    
    # Count pools per chain
    chain_counts = {}
    for pool_id in adapters.keys():
        parts = pool_id.split(":")
        if len(parts) >= 2:
            chain = parts[1]
            chain_counts[chain] = chain_counts.get(chain, 0) + 1
    
    print(f"\n🌐 Chain coverage: {chain_counts}")
    print(f"🎯 Chains in config: {chains}")
    
    # We should have significant Base coverage
    if chain_counts.get("base", 0) < 21:
        print("❌ Insufficient Base chain coverage")
        return False
    
    print("✅ Good Base chain coverage")
    return True


def test_new_protocols():
    """Test that new protocols are configured."""
    with CONFIG_PATH.open() as f:
        config = json.load(f)
    
    adapters = config.get("adapters", {})
    
    # Check for newly added protocols
    new_protocol_markers = [
        "morpho",
        "moonwell",
        "comet",
        "yearn",
    ]
    
    found_markers = set()
    for pool_id in adapters.keys():
        pool_id_lower = pool_id.lower()
        for marker in new_protocol_markers:
            if marker in pool_id_lower:
                found_markers.add(marker)
    
    print(f"\n🆕 New protocol types found: {sorted(found_markers)}")
    
    if len(found_markers) < 3:
        print("❌ Not enough new protocol coverage")
        return False
    
    print("✅ New protocols successfully added")
    return True


def test_config_structure():
    """Test that config has all required sections."""
    with CONFIG_PATH.open() as f:
        config = json.load(f)
    
    required_sections = ["chains", "adapters", "sources", "vault", "selection", "autopause"]
    missing_sections = [s for s in required_sections if s not in config]
    
    if missing_sections:
        print(f"❌ Missing config sections: {missing_sections}")
        return False
    
    print("✅ All required config sections present")
    return True


def main():
    """Run all tests."""
    print("=" * 80)
    print("ADAPTER EXPANSION TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("Config Structure", test_config_structure),
        ("Adapter Types", test_adapter_types),
        ("Adapter Count", test_adapter_count),
        ("Protocol Diversity", test_protocol_diversity),
        ("Asset Diversity", test_asset_diversity),
        ("Chain Coverage", test_chain_coverage),
        ("New Protocols", test_new_protocols),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        print("-" * 80)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    print("=" * 80)
    
    if passed == total:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
