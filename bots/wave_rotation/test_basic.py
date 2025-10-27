#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Basic smoke tests for wave rotation strategy."""

import importlib
import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    modules = [
        "strategy",
        "data_sources",
        "scoring",
        "executor",
        "portfolio",
        "treasury",
        "onchain",
    ]

    skipped = []
    imported = []

    for module in modules:
        try:
            importlib.import_module(module)
            imported.append(module)
        except ModuleNotFoundError as exc:
            # Optional dependency missing: skip the module but keep the test informative.
            missing = exc.name or "unknown"
            if missing == module or missing.startswith("bots.w"):
                raise
            skipped.append((module, missing))

    for name in imported:
        print(f"✓ Imported {name}")
    for name, dep in skipped:
        print(f"⊘ Skipped {name} (missing optional dependency: {dep})")

    assert imported, "At least one module should import successfully"

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
        "tvl_usd": 1_000_000,
        "fee_pct": 0.01,
        "risk_score": 0.2,
    }
    score = normalized_score(pool, adapter_src="explicit", cfg={})
    expected_score = daily_rate(pool["apy"]) / (1 + pool["fee_pct"] * (1 - pool["risk_score"]))
    assert abs(score - expected_score) < 1e-9, "Score should follow the CODEX_RULES formula"
    print(f"✓ normalized_score = {score:.6f}")
    

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


def test_ops_guard_requires_positive_delta(monkeypatch):
    """The economic guard blocks moves when the score delta is not positive."""

    from ops_guard import should_move

    for name in [
        "MIN_EDGE_SCORE",
        "MIN_EDGE_ETH",
        "MIN_EDGE_USD",
        "ETH_PRICE_USD",
        "EDGE_GAS_MULTIPLIER",
    ]:
        monkeypatch.delenv(name, raising=False)

    ok, note = should_move(
        capital_eth=10.0,
        score_best=0.009,
        score_current=0.01,
        est_move_gas=0,
        w3=None,
    )

    assert ok is False
    assert note.startswith("edge:delta<=0")


def test_ops_guard_allows_positive_edge_without_web3(monkeypatch):
    """When Web3 is unavailable the guard still allows profitable moves."""

    from ops_guard import should_move

    for name in [
        "MIN_EDGE_SCORE",
        "MIN_EDGE_ETH",
        "MIN_EDGE_USD",
        "ETH_PRICE_USD",
        "EDGE_GAS_MULTIPLIER",
    ]:
        monkeypatch.delenv(name, raising=False)

    ok, note = should_move(
        capital_eth=5.0,
        score_best=0.012,
        score_current=0.01,
        est_move_gas=0,
        w3=None,
    )

    assert ok is True
    assert note.startswith("edge:ok")
    assert note.endswith("gas=web3_missing")


def test_ops_guard_respects_gas_cost(monkeypatch):
    """The guard compares expected gain against the estimated gas cost."""

    from ops_guard import should_move

    class DummyEth:
        def __init__(self, gas_price):
            self.gas_price = gas_price

    class DummyWeb3:
        def __init__(self, gas_price):
            self.eth = DummyEth(gas_price)

    w3 = DummyWeb3(gas_price=20_000_000_000)  # 20 gwei

    monkeypatch.setenv("EDGE_GAS_MULTIPLIER", "1.0")

    ok, note = should_move(
        capital_eth=1.0,
        score_best=0.0101,
        score_current=0.01,
        est_move_gas=500_000,
        w3=w3,
    )
    assert ok is False
    assert note.startswith("edge:gas>")

    ok, note = should_move(
        capital_eth=10.0,
        score_best=0.012,
        score_current=0.01,
        est_move_gas=200_000,
        w3=w3,
    )
    assert ok is True
    assert "edge:ok" in note
    assert "gas=" in note


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
            result = test_func()
            if result is False:
                failed += 1
            else:
                passed += 1
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
