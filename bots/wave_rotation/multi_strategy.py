#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Multi-Strategy Optimizer for Attuario Wallet

Automatically allocates wallet funds across multiple pools based on:
- Asset compatibility
- APY scores
- Risk factors
- Available liquidity (TVL)

Features:
- Multi-asset wallet scanning
- Automatic pool matching per asset
- Greedy optimization algorithm
- Configurable buffer reserve
- Integration with existing adapters
- Treasury automation support
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from web3 import Web3
except ModuleNotFoundError:
    Web3 = None

from adapters import get_adapter
from data_sources import fetch_pools_scoped
from logger import timestamp_now
from scoring import normalized_score


@dataclass
class AllocationPlan:
    """Represents an allocation decision for a specific asset to a pool."""
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


@dataclass
class MultiStrategyConfig:
    """Configuration for multi-strategy optimizer."""
    enabled: bool
    buffer_percent: float
    min_investment_per_pool: float
    max_pools_per_asset: int
    
    @staticmethod
    def load() -> "MultiStrategyConfig":
        """Load configuration from environment variables."""
        enabled = os.getenv("MULTI_STRATEGY_ENABLED", "false").strip().lower() in {
            "1", "true", "yes", "on"
        }
        
        buffer_percent = float(os.getenv("STRATEGY_BUFFER_PERCENT", "5.0"))
        buffer_percent = max(0.0, min(100.0, buffer_percent))
        
        min_investment = float(os.getenv("MIN_INVESTMENT_PER_POOL", "0.001"))
        max_pools = int(os.getenv("MAX_POOLS_PER_ASSET", "3"))
        
        return MultiStrategyConfig(
            enabled=enabled,
            buffer_percent=buffer_percent,
            min_investment_per_pool=min_investment,
            max_pools_per_asset=max(1, max_pools),
        )


def _get_adapter_config(config_dict: dict, pool_id: str) -> Optional[Dict[str, object]]:
    """Get adapter configuration for a given pool ID."""
    adapters = config_dict.get("adapters", {})
    
    if pool_id in adapters:
        return adapters[pool_id]
    
    key_with_prefix = pool_id if pool_id.startswith("pool:") else f"pool:{pool_id}"
    if key_with_prefix in adapters:
        return adapters[key_with_prefix]
    
    key_without_prefix = pool_id[5:] if pool_id.startswith("pool:") else pool_id
    if key_without_prefix in adapters:
        return adapters[key_without_prefix]
    
    return None


def _get_required_tokens(adapter_cfg: Dict[str, object]) -> List[str]:
    """Extract required token addresses from adapter configuration."""
    tokens = []
    adapter_type = str(adapter_cfg.get("type") or "").lower()
    
    # Define which fields contain token addresses per adapter type
    token_fields = {
        "erc4626": ["asset"],
        "yearn": ["asset"],
        "comet": ["asset"],
        "ctoken": ["asset"],
        "aave_v3": ["asset"],
        "morpho": ["asset"],
        "vaultcraft": ["asset"],
        "yield_yak": ["asset"],
        "peapods_finance": ["asset"],
        "lp_beefy_aero": ["token0", "token1"],
        "uniswap_v2": ["token0", "token1"],
        "uniswap_v3": ["token0", "token1"],
        "aerodrome_v1": ["token0", "token1"],
        "aerodrome_slipstream": ["token0", "token1"],
        "raydium_amm": ["token0", "token1"],
        "hyperion": ["token0", "token1"],
        "etherex_cl": ["token0", "token1"],
    }
    
    fields = token_fields.get(adapter_type, [])
    
    for field in fields:
        value = adapter_cfg.get(field)
        if not value:
            continue
        
        # Handle ${ENV_VAR} format
        if isinstance(value, str):
            if value.startswith("${") and value.endswith("}"):
                env_name = value[2:-1]
                value = os.getenv(env_name, "")
            
            if value and value.startswith("0x"):
                try:
                    tokens.append(Web3.to_checksum_address(value).lower() if Web3 else value.lower())
                except Exception:
                    tokens.append(value.lower())
    
    return tokens


def match_pools_to_assets(
    pools: List[Dict],
    wallet_balances: Dict[str, float],
    config_dict: dict,
    multi_config: MultiStrategyConfig,
) -> Dict[str, List[Tuple[Dict, float]]]:
    """
    Match available pools to wallet assets.
    
    Returns:
        Dict mapping asset_address -> [(pool, score), ...]
        Sorted by score (highest first)
    """
    matches: Dict[str, List[Tuple[Dict, float]]] = {}
    
    for pool in pools:
        pool_id = pool.get("pool_id", "")
        if not pool_id:
            continue
        
        # Get adapter configuration
        adapter_cfg = _get_adapter_config(config_dict, pool_id)
        if not adapter_cfg:
            continue
        
        # Get required tokens for this pool
        required_tokens = _get_required_tokens(adapter_cfg)
        if not required_tokens:
            continue
        
        # Calculate score for this pool
        score = normalized_score(pool)
        if score <= 0:
            continue
        
        # Match to assets in wallet
        for token_addr in required_tokens:
            balance = wallet_balances.get(token_addr, 0.0)
            if balance <= 0:
                continue
            
            if token_addr not in matches:
                matches[token_addr] = []
            
            matches[token_addr].append((pool, score))
    
    # Sort each asset's pools by score (descending)
    for asset_addr in matches:
        matches[asset_addr].sort(key=lambda x: x[1], reverse=True)
        # Limit to max_pools_per_asset
        matches[asset_addr] = matches[asset_addr][:multi_config.max_pools_per_asset]
    
    return matches


def optimize_allocations(
    asset_matches: Dict[str, List[Tuple[Dict, float]]],
    wallet_balances: Dict[str, float],
    token_labels: Dict[str, str],
    multi_config: MultiStrategyConfig,
    eth_price_usd: float = 3000.0,
) -> List[AllocationPlan]:
    """
    Optimize asset allocation using greedy algorithm.
    
    Strategy:
    1. For each asset, allocate to the highest-scored pool first
    2. Apply buffer reserve (keep buffer_percent unallocated)
    3. Respect minimum investment threshold
    
    Args:
        asset_matches: Dict of asset -> [(pool, score), ...]
        wallet_balances: Current wallet balances per asset
        token_labels: Human-readable labels for tokens
        multi_config: Multi-strategy configuration
        eth_price_usd: ETH price for USD value calculation
    
    Returns:
        List of AllocationPlan objects
    """
    allocations: List[AllocationPlan] = []
    buffer_ratio = multi_config.buffer_percent / 100.0
    
    # Sort assets by highest pool score to prioritize best opportunities
    sorted_assets = sorted(
        asset_matches.items(),
        key=lambda x: x[1][0][1] if x[1] else 0.0,  # First pool's score
        reverse=True
    )
    
    for asset_addr, pool_matches in sorted_assets:
        balance = wallet_balances.get(asset_addr, 0.0)
        if balance <= 0:
            continue
        
        # Calculate allocatable amount (reserve buffer)
        allocatable = balance * (1.0 - buffer_ratio)
        if allocatable < multi_config.min_investment_per_pool:
            continue
        
        # For simplicity, allocate all to the best pool
        # (Can be extended to split across multiple pools in the future)
        if pool_matches:
            best_pool, best_score = pool_matches[0]
            
            # Estimate USD value (rough approximation)
            # Assumes ETH-like value; could be improved with price feeds
            allocation_usd = allocatable * eth_price_usd if asset_addr == "native" else allocatable * 1.0
            
            allocation = AllocationPlan(
                asset_address=asset_addr,
                asset_label=token_labels.get(asset_addr, asset_addr[:8]),
                asset_balance=balance,
                pool_id=best_pool.get("pool_id", ""),
                pool_name=best_pool.get("name", ""),
                pool_chain=best_pool.get("chain", ""),
                pool_score=best_score,
                pool_apy=best_pool.get("apy", 0.0),
                allocation_amount=allocatable,
                allocation_usd=allocation_usd,
            )
            allocations.append(allocation)
    
    return allocations


def execute_allocations(
    allocations: List[AllocationPlan],
    config_dict: dict,
    w3,
    account,
    dry_run: bool = True,
) -> Dict[str, str]:
    """
    Execute allocation plans by calling adapters.
    
    Args:
        allocations: List of allocation plans
        config_dict: Configuration dictionary with adapter info
        w3: Web3 instance
        account: Account object with address
        dry_run: If True, simulate without executing transactions
    
    Returns:
        Dict mapping pool_id -> execution status
    """
    results: Dict[str, str] = {}
    
    for allocation in allocations:
        pool_id = allocation.pool_id
        
        if dry_run:
            results[pool_id] = f"dry_run:deposit:{allocation.allocation_amount:.6f}"
            continue
        
        # Get adapter for this pool
        adapter, err = get_adapter(pool_id, config_dict, w3, account)
        if adapter is None:
            results[pool_id] = f"error:no_adapter:{err}"
            continue
        
        try:
            # Execute deposit
            result = adapter.deposit_all()
            status = result.get("status", "unknown")
            tx = result.get("deposit_tx", "")
            
            if status == "ok" and tx:
                results[pool_id] = f"ok:{tx}"
            else:
                results[pool_id] = f"error:{status}"
        
        except Exception as exc:
            results[pool_id] = f"error:exception:{str(exc)[:50]}"
    
    return results


def save_allocation_state(
    allocations: List[AllocationPlan],
    execution_results: Dict[str, str],
    state_file: Path,
) -> None:
    """Save allocation state to JSON file."""
    state = {
        "timestamp": timestamp_now(),
        "allocations": {},
        "buffer_reserved": True,
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
        }
    
    with state_file.open("w") as f:
        json.dump(state, f, indent=2)


def execute_multi_strategy(
    config_dict: dict,
    wallet_balances: Dict[str, float],
    token_labels: Dict[str, str],
    w3=None,
    account=None,
    dry_run: bool = True,
) -> Tuple[List[AllocationPlan], Dict[str, str]]:
    """
    Main entry point for multi-strategy execution.
    
    Args:
        config_dict: Configuration dictionary
        wallet_balances: Current wallet balances
        token_labels: Token address to label mapping
        w3: Web3 instance (optional)
        account: Account object (optional)
        dry_run: If True, simulate without executing
    
    Returns:
        Tuple of (allocations, execution_results)
    """
    # Load multi-strategy configuration
    multi_config = MultiStrategyConfig.load()
    
    if not multi_config.enabled:
        return [], {"status": "disabled"}
    
    # Fetch available pools
    pools, source_name, stats = fetch_pools_scoped(config_dict)
    
    if not pools:
        return [], {"status": "no_pools_available"}
    
    print(f"[multi-strategy] Fetched {len(pools)} pools from {source_name}")
    
    # Match pools to wallet assets
    asset_matches = match_pools_to_assets(
        pools,
        wallet_balances,
        config_dict,
        multi_config,
    )
    
    if not asset_matches:
        return [], {"status": "no_compatible_pools"}
    
    print(f"[multi-strategy] Matched {len(asset_matches)} assets to pools")
    
    # Get ETH price for USD calculations
    eth_price_usd = float(os.getenv("ETH_PRICE_USD", "3000.0"))
    
    # Optimize allocations
    allocations = optimize_allocations(
        asset_matches,
        wallet_balances,
        token_labels,
        multi_config,
        eth_price_usd,
    )
    
    if not allocations:
        return [], {"status": "no_viable_allocations"}
    
    print(f"[multi-strategy] Generated {len(allocations)} allocation plans")
    
    # Execute allocations
    execution_results = execute_allocations(
        allocations,
        config_dict,
        w3,
        account,
        dry_run,
    )
    
    # Save state
    state_file = Path(__file__).resolve().parent / "multi_strategy_state.json"
    save_allocation_state(allocations, execution_results, state_file)
    
    return allocations, execution_results


def print_allocation_summary(
    allocations: List[AllocationPlan],
    execution_results: Dict[str, str],
) -> None:
    """Print human-readable summary of allocations."""
    if not allocations:
        print("[multi-strategy] No allocations generated")
        return
    
    print("\n" + "="*70)
    print("MULTI-STRATEGY ALLOCATION SUMMARY")
    print("="*70)
    
    total_usd = sum(a.allocation_usd for a in allocations)
    
    for i, alloc in enumerate(allocations, 1):
        print(f"\n[{i}] {alloc.asset_label}")
        print(f"    Pool: {alloc.pool_name} ({alloc.pool_chain})")
        print(f"    Amount: {alloc.allocation_amount:.6f} (${alloc.allocation_usd:.2f})")
        print(f"    Score: {alloc.pool_score:.6f} | APY: {alloc.pool_apy:.2%}")
        
        result = execution_results.get(alloc.pool_id, "unknown")
        print(f"    Status: {result}")
    
    print(f"\nTotal Value Allocated: ${total_usd:.2f}")
    print("="*70 + "\n")
