#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Updated test suite for the multi-strategy optimizer."""

import os
from pathlib import Path
from typing import Dict, List

import pytest

from multi_strategy import (
    AllocationPlan,
    MultiStrategyConfig,
    build_allocation_plan,
    execute_allocations,
    execute_multi_strategy,
    generate_opportunities,
    print_allocation_summary,
    _build_holdings_map,
)
from wallet_scanner import WalletHolding

# Configure environment for deterministic tests
os.environ.update(
    {
        "MULTI_STRATEGY_ENABLED": "true",
        "STRATEGY_BUFFER_PERCENT": "10.0",
        "MIN_INVESTMENT_PER_POOL_USD": "100",
        "MAX_POOLS_PER_ASSET": "2",
        "MIN_DUST_USD": "50",
        "TREND_WINDOW_D": "14",
        "TREND_Z_MIN": "0.1",
        "TREND_Z_CAP": "3.0",
        "TREND_VOL_CAP": "0.05",
        "TREND_DD_CAP": "0.25",
        "W_APY": "0.4",
        "W_TR": "0.5",
        "W_VOL": "0.05",
        "W_DD": "0.05",
        "EDGE_MIN_NET_USD": "0.1",
        "HORIZON_DAYS": "1.0",
        "GAS_WITHDRAW_COST_USD": "0.0",
        "GAS_DEPOSIT_COST_USD": "0.0",
        "SWAP_FEE_BPS": "0.0",
        "EDGE_SLIPPAGE_BPS": "0.0",
    }
)

BEEFY_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"
USDC_ADDRESS = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"


def sample_holdings() -> List[WalletHolding]:
    return [
        WalletHolding(
            address=WETH_ADDRESS,
            label="WETH",
            amount=2.0,
            usd_value=6000.0,
            unit_price_usd=3000.0,
            is_native=False,
        ),
        WalletHolding(
            address=USDC_ADDRESS,
            label="USDC",
            amount=1500.0,
            usd_value=1500.0,
            unit_price_usd=1.0,
            is_native=False,
        ),
    ]


def sample_pools() -> List[Dict[str, object]]:
    return [
        {
            "pool_id": "base:aave-v3:WETH",
            "name": "Aave V3 WETH",
            "chain": "base",
            "apy": 0.06,
            "tvl_usd": 12_000_000,
            "risk_score": 0.1,
            "fee_pct": 0.01,
        },
        {
            "pool_id": "base:morpho:USDC",
            "name": "Morpho USDC",
            "chain": "base",
            "apy": 0.08,
            "tvl_usd": 8_000_000,
            "risk_score": 0.15,
            "fee_pct": 0.01,
        },
    ]


def sample_config_dict() -> Dict[str, object]:
    return {
        "chains": ["base"],
        "sources": {"defillama": False},
        "adapters": {
            "pool:base:aave-v3:WETH": {
                "type": "aave_v3",
                "asset": WETH_ADDRESS,
            },
            "pool:base:morpho:USDC": {
                "type": "erc4626",
                "asset": USDC_ADDRESS,
            },
        },
    }


def test_config_loading():
    config = MultiStrategyConfig.load()
    assert config.enabled is True
    assert config.buffer_percent == pytest.approx(10.0)
    assert config.min_investment_usd == pytest.approx(100.0)
    assert config.max_pools_per_asset == 2
    assert config.min_dust_usd == pytest.approx(50.0)
    assert config.trend.window_days == 14
    assert config.edge.min_net_usd == pytest.approx(0.1)


def test_generate_opportunities_and_plan():
    config = MultiStrategyConfig.load()
    holdings = sample_holdings()
    pools = sample_pools()
    config_dict = sample_config_dict()

    opportunities = generate_opportunities(
        pools,
        _build_holdings_map(holdings),
        config_dict,
        config,
    )

    assert WETH_ADDRESS.lower() in opportunities
    assert USDC_ADDRESS.lower() in opportunities
    assert all(opportunities[addr] for addr in opportunities)

    plan = build_allocation_plan(holdings, opportunities, config)
    assert plan, "Expected at least one allocation plan"
    for alloc in plan:
        assert alloc.edge_net_usd >= 0.0
        assert alloc.allocation_usd >= config.min_investment_usd


def test_execute_allocations_dry_run():
    plan = [
        AllocationPlan(
            asset_address=WETH_ADDRESS.lower(),
            asset_label="WETH",
            asset_balance=2.0,
            pool_id="base:aave-v3:WETH",
            pool_name="Aave V3 WETH",
            pool_chain="base",
            pool_score=0.5,
            pool_apy=0.06,
            allocation_amount=1.5,
            allocation_usd=4500.0,
            trend_z=1.2,
            edge_net_usd=25.0,
        )
    ]
    results = execute_allocations(plan, sample_config_dict(), w3=None, account=None, dry_run=True)
    assert "base:aave-v3:WETH" in results
    assert results["base:aave-v3:WETH"].startswith("dry_run")


def test_execute_multi_strategy(monkeypatch):
    config_dict = sample_config_dict()
    holdings = sample_holdings()
    wallet_balances = {h.address.lower(): h.amount for h in holdings}
    wallet_labels = {h.address.lower(): h.label for h in holdings}

    def fake_fetch_pools_scoped(_config):
        return sample_pools(), "stub", {"source": "stub"}

    monkeypatch.setattr("multi_strategy.fetch_pools_scoped", fake_fetch_pools_scoped)

    allocations, results = execute_multi_strategy(
        config_dict,
        holdings,
        wallet_balances,
        wallet_labels,
        w3=None,
        account=None,
        dry_run=True,
    )

    assert allocations, "Expected allocations from multi-strategy"
    assert all(plan.edge_net_usd >= 0 for plan in allocations)
    print_allocation_summary(allocations, results)

    state_path = Path(__file__).resolve().parent / "multi_strategy_state.json"
    assert state_path.exists()
    state_path.unlink()
