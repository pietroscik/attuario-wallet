#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Multi-Strategy Optimizer for Attuario Wallet.

The optimizer now operates in four stages:
1. Scan wallet holdings (normalized in USD)
2. Evaluate pool opportunities with trend-aware scoring
3. Build a diversified allocation plan per asset
4. Execute deposits (or simulate in dry-run mode)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from web3 import Web3  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Web3 = None  # type: ignore[assignment]

from adapter_utils import adapter_required_tokens, get_adapter_config
from adapters import get_adapter
from data_sources import fetch_pools_scoped
from logger import timestamp_now
from scoring import (
    EdgeConfig,
    TrendMetrics,
    TrendSignalConfig,
    compute_trend_metrics,
    compute_trend_score,
    net_edge_usd,
)
from wallet_scanner import WalletHolding


def _env_set(name: str) -> set[str]:
    raw = os.getenv(name, "")
    values: set[str] = set()
    if not raw:
        return values
    for part in raw.split(","):
        entry = part.strip()
        if entry:
            values.add(entry.lower())
    return values


POOL_ALLOWLIST = _env_set("POOL_ALLOWLIST")
POOL_DENYLIST = _env_set("POOL_DENYLIST")


@dataclass
class CandidateOpportunity:
    """Candidate pool opportunity for a specific asset."""

    pool: Dict[str, Any]
    adapter_cfg: Dict[str, object]
    asset_address: str
    asset_label: str
    apy: float
    composite_score: float
    score_components: Dict[str, float]
    trend_metrics: TrendMetrics


@dataclass
class AllocationPlan:
    """Planned allocation for a wallet holding."""

    asset_address: str
    asset_label: str
    asset_balance: float
    pool_id: str
    pool_name: str
    pool_chain: str
    pool_score: float
    pool_apy: float
    allocation_amount: float
    allocation_usd: float
    trend_z: float
    edge_net_usd: float
    edge_breakdown: Dict[str, float] = field(default_factory=dict)
    score_components: Dict[str, float] = field(default_factory=dict)


@dataclass
class MultiStrategyConfig:
    """Configuration bundle for the multi-strategy engine."""

    enabled: bool
    buffer_percent: float
    min_investment_usd: float
    max_pools_per_asset: int
    min_dust_usd: float
    trend: TrendSignalConfig
    edge: EdgeConfig
    include_withdraw_cost: bool = True

    @property
    def buffer_ratio(self) -> float:
        return max(0.0, min(self.buffer_percent / 100.0, 0.95))

    @classmethod
    def load(cls) -> "MultiStrategyConfig":
        enabled = os.getenv("MULTI_STRATEGY_ENABLED", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        buffer_percent = float(os.getenv("STRATEGY_BUFFER_PERCENT", "5.0"))
        try:
            min_investment_usd = float(
                os.getenv("MIN_INVESTMENT_PER_POOL_USD", os.getenv("MIN_INVESTMENT_PER_POOL", "50"))
            )
        except ValueError:
            min_investment_usd = 50.0
        if min_investment_usd <= 0:
            min_investment_usd = 50.0

        max_pools = int(os.getenv("MAX_POOLS_PER_ASSET", "1"))
        min_dust = float(os.getenv("MIN_DUST_USD", "0.25"))

        include_withdraw = os.getenv("EDGE_INCLUDE_WITHDRAW", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        trend_cfg = TrendSignalConfig.from_env()
        edge_cfg = EdgeConfig.from_env()

        return cls(
            enabled=enabled,
            buffer_percent=max(0.0, buffer_percent),
            min_investment_usd=max(0.0, min_investment_usd),
            max_pools_per_asset=max(1, max_pools),
            min_dust_usd=max(0.0, min_dust),
            trend=trend_cfg,
            edge=edge_cfg,
            include_withdraw_cost=include_withdraw,
        )


def _build_holdings_map(holdings: Iterable[WalletHolding]) -> Dict[str, WalletHolding]:
    mapping: Dict[str, WalletHolding] = {}
    for holding in holdings:
        mapping[holding.address.lower()] = holding
        if holding.is_native:
            mapping.setdefault("native", holding)
    return mapping


def generate_opportunities(
    pools: List[Dict[str, Any]],
    holdings_map: Dict[str, WalletHolding],
    config_dict: Dict[str, Any],
    multi_config: MultiStrategyConfig,
) -> Dict[str, List[CandidateOpportunity]]:
    """Build opportunity list per asset given available pools."""

    opportunities: Dict[str, List[CandidateOpportunity]] = {}
    allowed_chains = {chain.lower() for chain in config_dict.get("chains", [])}

    for pool in pools:
        pool_id = str(pool.get("pool_id") or "").strip()
        if not pool_id:
            continue

        pool_key = pool_id.lower()
        if POOL_ALLOWLIST and pool_key not in POOL_ALLOWLIST:
            continue
        if POOL_DENYLIST and pool_key in POOL_DENYLIST:
            continue

        chain = str(pool.get("chain") or "").lower()
        if allowed_chains and chain and chain not in allowed_chains:
            continue

        adapter_cfg = get_adapter_config(config_dict, pool_id)
        if not adapter_cfg:
            continue

        required_tokens = adapter_required_tokens(adapter_cfg)
        if len(required_tokens) != 1:
            # Skip pools requiring multiple assets for now
            continue

        token_addr, token_label = required_tokens[0]
        token_addr_lower = token_addr.lower()

        holding = holdings_map.get(token_addr_lower)
        if holding is None and token_addr_lower == "native":
            holding = holdings_map.get("native")
        if holding is None:
            continue

        apy = float(pool.get("apy") or 0.0)
        if apy <= 0:
            continue

        trend_metrics = compute_trend_metrics(pool_id, pool, multi_config.trend)
        if not trend_metrics.ok or trend_metrics.trend_z < multi_config.trend.z_min:
            continue

        composite_score, components = compute_trend_score(apy, trend_metrics, multi_config.trend)
        if composite_score <= 0:
            continue

        candidate = CandidateOpportunity(
            pool=pool,
            adapter_cfg=adapter_cfg,
            asset_address=token_addr_lower,
            asset_label=holding.label,
            apy=apy,
            composite_score=composite_score,
            score_components=components,
            trend_metrics=trend_metrics,
        )
        opportunities.setdefault(token_addr_lower, []).append(candidate)

    for asset_addr, items in opportunities.items():
        items.sort(key=lambda c: c.composite_score, reverse=True)

    return opportunities


def build_allocation_plan(
    holdings: List[WalletHolding],
    opportunities: Dict[str, List[CandidateOpportunity]],
    multi_config: MultiStrategyConfig,
) -> List[AllocationPlan]:
    """Construct allocation plan ensuring diversification and positive net edge."""

    plans: List[AllocationPlan] = []
    buffer_ratio = multi_config.buffer_ratio

    for holding in holdings:
        asset_addr = holding.address.lower()
        if holding.usd_value < multi_config.min_dust_usd:
            continue

        asset_opps = opportunities.get(asset_addr, [])
        if not asset_opps:
            continue

        available_amount = holding.amount * (1.0 - buffer_ratio)
        if available_amount <= 0:
            continue
        available_usd = available_amount * holding.unit_price_usd
        if available_usd < multi_config.min_investment_usd:
            continue

        top_candidates = [
            c for c in asset_opps if c.composite_score > 0
        ][: multi_config.max_pools_per_asset]
        if not top_candidates:
            continue

        weights = [max(c.composite_score, 0.0) for c in top_candidates]
        total_weight = sum(weights)
        if total_weight <= 0:
            continue

        remaining_usd = available_usd
        remaining_amount = available_amount

        for candidate, weight in zip(top_candidates, weights):
            share = weight / total_weight
            allocation_usd = remaining_usd * share
            if allocation_usd < multi_config.min_investment_usd:
                continue

            net_edge, breakdown = net_edge_usd(
                candidate.apy,
                allocation_usd,
                multi_config.edge,
                include_withdraw=multi_config.include_withdraw_cost,
            )
            if net_edge < multi_config.edge.min_net_usd:
                continue

            allocation_amount = allocation_usd / (holding.unit_price_usd or 1e-9)
            if allocation_amount <= 0:
                continue

            plan = AllocationPlan(
                asset_address=asset_addr,
                asset_label=holding.label,
                asset_balance=holding.amount,
                pool_id=str(candidate.pool.get("pool_id", "")),
                pool_name=str(candidate.pool.get("name", "")),
                pool_chain=str(candidate.pool.get("chain", "")),
                pool_score=candidate.composite_score,
                pool_apy=candidate.apy,
                allocation_amount=allocation_amount,
                allocation_usd=allocation_usd,
                trend_z=candidate.trend_metrics.trend_z,
                edge_net_usd=net_edge,
                edge_breakdown=breakdown,
                score_components=candidate.score_components,
            )
            plans.append(plan)

            remaining_usd -= allocation_usd
            remaining_amount -= allocation_amount
            if remaining_usd < multi_config.min_investment_usd or remaining_amount <= 0:
                break

    plans.sort(key=lambda p: p.edge_net_usd, reverse=True)
    return plans


def execute_allocations(
    allocations: List[AllocationPlan],
    config_dict: dict,
    w3,
    account,
    dry_run: bool = True,
) -> Dict[str, str]:
    """Execute allocation plans using configured adapters."""

    results: Dict[str, str] = {}
    for plan in allocations:
        pool_id = plan.pool_id
        if dry_run:
            results[pool_id] = (
                f"dry_run:deposit:{plan.allocation_amount:.6f} (edge=${plan.edge_net_usd:.2f})"
            )
            continue

        adapter, err = get_adapter(pool_id, config_dict, w3, account)
        if adapter is None:
            results[pool_id] = f"error:no_adapter:{err}"
            continue

        try:
            result = adapter.deposit_all()
            status = result.get("status", "unknown")
            tx = result.get("deposit_tx", "")
            if status == "ok" and tx:
                results[pool_id] = f"ok:{tx}"
            else:
                results[pool_id] = f"error:{status}"
        except Exception as exc:  # pragma: no cover - defensive
            results[pool_id] = f"error:exception:{str(exc)[:50]}"
    return results


def save_allocation_state(
    allocations: List[AllocationPlan],
    execution_results: Dict[str, str],
    state_file: Path,
) -> None:
    """Persist allocation state to JSON for observability."""

    state = {
        "timestamp": timestamp_now(),
        "allocations": {},
        "execution_results": execution_results,
    }
    for alloc in allocations:
        state["allocations"][alloc.asset_label] = {
            "pool": alloc.pool_id,
            "pool_name": alloc.pool_name,
            "chain": alloc.pool_chain,
            "amount": alloc.allocation_amount,
            "usd_value": alloc.allocation_usd,
            "score": alloc.pool_score,
            "apy": alloc.pool_apy,
            "trend_z": alloc.trend_z,
            "edge_net_usd": alloc.edge_net_usd,
        }

    with state_file.open("w") as fh:
        json.dump(state, fh, indent=2)


def execute_multi_strategy(
    config_dict: dict,
    holdings: List[WalletHolding],
    wallet_balances: Dict[str, float],
    wallet_labels: Dict[str, str],
    w3=None,
    account=None,
    dry_run: bool = True,
) -> Tuple[List[AllocationPlan], Dict[str, str]]:
    """
    Execute multi-strategy allocation and return (allocations, execution_results).
    """

    # Backwards compatibility: existing callers still pass these mappings
    del wallet_balances, wallet_labels

    multi_config = MultiStrategyConfig.load()
    if not multi_config.enabled:
        return [], {"status": "disabled"}

    filtered_holdings = [
        h for h in holdings if h.usd_value >= multi_config.min_dust_usd
    ]
    if not filtered_holdings:
        return [], {"status": "no_holdings"}

    pools, source_name, stats = fetch_pools_scoped(config_dict)
    if not pools:
        return [], {"status": "no_pools_available"}

    print(f"[multi-strategy] Fetched {len(pools)} pools from {source_name}")
    holdings_map = _build_holdings_map(filtered_holdings)

    opportunities = generate_opportunities(
        pools,
        holdings_map,
        config_dict,
        multi_config,
    )
    if not opportunities:
        return [], {"status": "no_opportunities"}

    plan = build_allocation_plan(
        filtered_holdings,
        opportunities,
        multi_config,
    )
    if not plan:
        return [], {"status": "no_viable_allocations"}

    print(f"[multi-strategy] Generated {len(plan)} allocation plans")

    execution_results = execute_allocations(
        plan,
        config_dict,
        w3,
        account,
        dry_run,
    )

    state_file = Path(__file__).resolve().parent / "multi_strategy_state.json"
    save_allocation_state(plan, execution_results, state_file)

    return plan, execution_results


def print_allocation_summary(
    allocations: List[AllocationPlan],
    execution_results: Dict[str, str],
) -> None:
    """Print summary for CLI / logs."""

    if not allocations:
        print("[multi-strategy] No allocations generated")
        return

    print("\n" + "=" * 70)
    print("MULTI-STRATEGY ALLOCATION SUMMARY")
    print("=" * 70)

    total_usd = sum(a.allocation_usd for a in allocations)
    for idx, alloc in enumerate(allocations, 1):
        status = execution_results.get(alloc.pool_id, "unknown")
        print(f"\n[{idx}] {alloc.asset_label} → {alloc.pool_name} ({alloc.pool_chain})")
        print(f"    Amount: {alloc.allocation_amount:.6f}  (${alloc.allocation_usd:.2f})")
        print(f"    APY: {alloc.pool_apy:.2%} | Trend Z: {alloc.trend_z:.2f}")
        print(f"    Net Edge: ${alloc.edge_net_usd:.2f} (costs: ${alloc.edge_breakdown.get('total_cost', 0.0):.2f})")
        print(f"    Score components: {alloc.score_components}")
        print(f"    Status: {status}")

    print(f"\nTotal Value Allocated: ${total_usd:.2f}")
    print("=" * 70 + "\n")
