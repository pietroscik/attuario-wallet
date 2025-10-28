#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Basic smoke tests for wave rotation strategy."""

import importlib
import json
import sys
from pathlib import Path

import pytest

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
    cost_daily = pool["fee_pct"] / 365.0
    expected_score = daily_rate(pool["apy"]) / (1 + cost_daily * (1 - pool["risk_score"]))
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


def test_effective_reinvest_ratio_threshold():
    """Treasury payout should trigger only above the EUR threshold."""

    try:
        from strategy import effective_reinvest_ratio
    except ModuleNotFoundError as exc:  # Optional deps missing for strategy import
        pytest.skip(f"strategy import skipped: missing dependency {exc.name}")

    base_ratio = 0.5
    fx_rate = 1800.0
    min_eur = 0.5

    # Profit too small: the 50% treasury share would be <0.5 EUR → reinvest everything.
    ratio_small = effective_reinvest_ratio(0.0001, base_ratio, fx_rate=fx_rate, min_payout_eur=min_eur)
    assert ratio_small == 1.0

    # Profit large enough: treasury share clears the threshold → honour the base ratio.
    ratio_large = effective_reinvest_ratio(0.01, base_ratio, fx_rate=fx_rate, min_payout_eur=min_eur)
    assert abs(ratio_large - base_ratio) < 1e-9

    print(
        "✓ effective_reinvest_ratio threshold logic: small profit reinvested, large profit splits"
    )


def test_reinvestment_simulator_matches_strategy(tmp_path):
    """La simulazione deve rispettare la soglia treasury e mantenere il capitale investito."""

    from utils import reinvestment_simulator as sim

    cycles = sim.run_simulation(
        initial_capital=10.0,
        returns=[0.01],
        fx_rate=2000.0,
        min_payout_eur=0.5,
    )
    assert len(cycles) == 1
    cycle = cycles[0]
    assert pytest.approx(cycle.reinvest_ratio, rel=1e-9) == 0.5
    assert pytest.approx(cycle.treasury_add, rel=1e-9) == 0.05
    assert pytest.approx(cycle.capital_after, rel=1e-9) == 10.05

    cycles_small = sim.run_simulation(
        initial_capital=10.0,
        returns=[0.00001],
        fx_rate=2000.0,
        min_payout_eur=0.5,
    )
    assert cycles_small[0].reinvest_ratio == 1.0
    assert cycles_small[0].treasury_add == 0.0

    log_path = tmp_path / "log.csv"
    log_path.write_text(
        "date,capital_before,capital_after,treasury_delta\n"
        "2024-01-01,10,10.05,0.5\n"
        "2024-01-02,10.05,9.95,0\n"
    )

    loaded_cycles = sim.load_cycles_from_log(log_path)
    assert len(loaded_cycles) == 2
    summary = sim.summarize_cycles(loaded_cycles)
    assert summary["cycles"] == 2
    assert pytest.approx(summary["capital_start"], rel=1e-9) == 10.0
    assert pytest.approx(summary["capital_end"], rel=1e-9) == 9.95
    assert summary["apy_effective"] < 0

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


def test_ops_guard_requires_current_score(monkeypatch):
    """If the current score is missing the guard should reject the move."""

    from ops_guard import should_move

    monkeypatch.delenv("MIN_EDGE_SCORE", raising=False)

    ok, note = should_move(
        capital_eth=10.0,
        score_best=0.02,
        score_current=None,
        est_move_gas=0,
        w3=None,
    )

    assert ok is False
    assert note == "edge:score_current_missing"


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
            self._gas_price = gas_price

        @property
        def gas_price(self):
            return self._gas_price

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


def test_strategy_print_status_cli(monkeypatch, tmp_path, capsys):
    """The CLI --print-status flag should render a concise status report."""

    try:
        import strategy
        from logger import append_log, COLUMNS
    except ModuleNotFoundError as exc:
        pytest.skip(f"strategy import skipped: missing dependency {exc.name}")

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "chains": ["base"],
                "min_tvl_usd": 100000,
                "delta_switch": 0.01,
                "reinvest_ratio": 0.5,
                "treasury_token": "USDC",
                "schedule_utc": "07:00",
                "stop_loss_daily": -0.1,
                "take_profit_daily": 0.05,
                "sources": {},
                "vault": {},
                "telegram": {"enabled": False},
                "adapters": {},
                "selection": {},
                "autopause": {},
            }
        )
    )

    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "pool_id": "pool:base:test",
                "pool_name": "Test Pool",
                "chain": "base",
                "score": 0.0123,
                "updated_at": "2025-01-01 00:00:00",
                "paused": False,
                "crisis_streak": 1,
                "last_crisis_at": "2024-12-31 23:00:00",
                "last_portfolio_move": "2025-01-01 00:30:00",
            }
        )
    )

    capital_file = tmp_path / "capital.txt"
    capital_file.write_text("101.000000")
    treasury_file = tmp_path / "treasury.txt"
    treasury_file.write_text("5.500000")
    log_file = tmp_path / "log.csv"

    row = {key: "" for key in COLUMNS}
    row.update(
        {
            "date": "2025-01-01 00:00:00",
            "pool": "Test Pool",
            "chain": "base",
            "status": "executed|portfolio:ok",
            "capital_after": "101.500000",
            "treasury_total": "5.750000",
        }
    )
    append_log(row, str(log_file))

    monkeypatch.setattr(strategy, "CAPITAL_FILE", capital_file)
    monkeypatch.setattr(strategy, "TREASURY_FILE", treasury_file)
    monkeypatch.setattr(strategy, "STATE_FILE", state_path)
    monkeypatch.setattr(strategy, "LOG_FILE", log_file)

    strategy.main(["--config", str(config_path), "--print-status"])

    captured = capsys.readouterr().out
    assert "Test Pool" in captured
    assert "score 0.012300" in captured
    assert "Ultimo log" in captured


def test_status_report_checklist(monkeypatch, tmp_path, capsys):
    """The status report checklist should highlight missing actions."""

    try:
        import status_report
        from logger import append_log, COLUMNS
    except ModuleNotFoundError as exc:
        pytest.skip(f"status_report import skipped: missing dependency {exc.name}")

    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "pool_id": "pool:base:test",
                "pool_name": "Test Pool",
                "chain": "base",
                "score": 0.01,
                "updated_at": "2025-01-01 00:00:00",
                "paused": False,
                "crisis_streak": 0,
            }
        )
    )

    capital_file = tmp_path / "capital.txt"
    capital_file.write_text("100.000000")
    treasury_file = tmp_path / "treasury.txt"
    treasury_file.write_text("0.000000")

    log_file = tmp_path / "log.csv"
    row = {key: "" for key in COLUMNS}
    row.update(
        {
            "date": "2025-01-01 00:00:00",
            "pool": "Test Pool",
            "chain": "base",
            "score": "0.010000",
            "capital_before": "100.000000",
            "capital_after": "100.500000",
            "treasury_delta": "0.000000",
            "roi_daily": "0.500000",
            "roi_total": "0.500000",
            "pnl_daily": "0.500000",
            "pnl_total": "0.500000",
            "status": "executed|portfolio:onchain_disabled",
        }
    )
    append_log(row, str(log_file))

    monkeypatch.setattr(status_report, "CAPITAL_FILE", capital_file)
    monkeypatch.setattr(status_report, "TREASURY_FILE", treasury_file)
    monkeypatch.setattr(status_report, "STATE_FILE", state_path)
    monkeypatch.setattr(status_report, "LOG_FILE", log_file)

    for name in [
        "ONCHAIN_ENABLED",
        "PORTFOLIO_AUTOMATION_ENABLED",
        "TREASURY_AUTOMATION_ENABLED",
    ]:
        monkeypatch.delenv(name, raising=False)

    status_report.main(["--checklist"])

    output = capsys.readouterr().out
    assert "=== Checklist ===" in output
    assert "Esecuzione on-chain: Disattivata" in output
    assert "Portfolio automation: Disattivata" in output
    assert "portfolio:onchain_disabled" in output

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
