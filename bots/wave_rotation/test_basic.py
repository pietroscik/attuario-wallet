#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Basic smoke tests for wave rotation strategy."""

import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    try:
        import strategy
        import data_sources
        import scoring
        import executor
        import portfolio
        import treasury
        import onchain
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_scoring_functions():
    """Test scoring functions."""
    from scoring import daily_rate, normalized_score
    
    # Test daily_rate conversion
    apy = 0.10  # 10% APY
    r_day = daily_rate(apy)
    expected = (1.10) ** (1/365) - 1
    assert abs(r_day - expected) < 1e-6, f"daily_rate failed: {r_day} != {expected}"
    print(f"✓ daily_rate(10% APY) = {r_day:.6f}")
    
    # Test normalized_score
    pool = {
        "apy": 0.15,
        "tvl_usd": 1000000,
        "perfFeeBps": 0,
        "mgmtFeeBps": 0,
    }
    config = {"selection": {"aggressive": True}}
    score = normalized_score(pool, adapter_src="explicit", cfg=config)
    assert score > 0, "Score should be positive for good pool"
    print(f"✓ normalized_score = {score:.6f}")
    
    return True

def test_data_normalization():
    """Test pool data normalization."""
    from data_sources import _normalize_defillama_pool
    
    raw = {
        "pool": "0x1234567890123456789012345678901234567890",
        "chain": "base",
        "project": "aave",
        "symbol": "USDC",
        "apy": 5.5,  # 5.5% as number
        "tvlUsd": 1500000,
    }
    
    normalized = _normalize_defillama_pool(raw)
    assert normalized["chain"] == "base"
    assert normalized["apy"] == 0.055  # Should be converted to decimal
    assert normalized["tvl_usd"] == 1500000
    print(f"✓ Pool normalization works: {normalized['pool_id']}")
    
    return True

def test_settle_day():
    """Test capital settlement logic."""
    from executor import settle_day
    
    capital = 100.0
    r_net = 0.05  # 5% return
    reinvest_ratio = 0.5
    
    profit, capital_new, treasury_delta = settle_day(capital, r_net, reinvest_ratio)
    
    assert profit == 5.0, f"Profit should be 5.0, got {profit}"
    assert capital_new == 102.5, f"New capital should be 102.5, got {capital_new}"
    assert treasury_delta == 2.5, f"Treasury should be 2.5, got {treasury_delta}"
    
    print(f"✓ settle_day: profit={profit}, new_capital={capital_new}, treasury={treasury_delta}")
    return True

def test_should_switch():
    """Test pool switching logic."""
    from scoring import should_switch
    
    # Test 1: No current pool -> should switch
    result = should_switch(
        best={"score": 0.001},
        current=None,
        min_delta=0.01,
    )
    assert result is True, "Should switch when no current pool"
    print("✓ should_switch: no current -> switch")
    
    # Test 2: Better pool by >1% -> should switch
    result = should_switch(
        best={"score": 0.0102},
        current={"score": 0.01},
        min_delta=0.01,
    )
    assert result is True, "Should switch when score improves by >1%"
    print("✓ should_switch: +2% improvement -> switch")
    
    # Test 3: Better pool but <1% -> should not switch
    result = should_switch(
        best={"score": 0.0105},
        current={"score": 0.0104},
        min_delta=0.01,
    )
    assert result is False, "Should not switch when improvement <1%"
    print("✓ should_switch: +0.96% improvement -> no switch")
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("Running basic smoke tests for Wave Rotation Strategy")
    print("=" * 60)
    
    tests = [
        ("Import Tests", test_imports),
        ("Scoring Functions", test_scoring_functions),
        ("Data Normalization", test_data_normalization),
        ("Capital Settlement", test_settle_day),
        ("Pool Switching Logic", test_should_switch),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\n{name}:")
        print("-" * 60)
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
