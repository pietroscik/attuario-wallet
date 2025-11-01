#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Adapter helper utilities shared across strategy components."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

try:
    from web3 import Web3  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Web3 = None  # type: ignore[assignment]

REQUIRED_TOKEN_FIELDS: Dict[str, Sequence[str]] = {
    "erc4626": ("asset",),
    "yearn": ("asset",),
    "comet": ("asset",),
    "ctoken": ("asset",),
    "aave_v3": ("asset",),
    "lp_beefy_aero": ("token0", "token1"),
    "uniswap_v2": ("token0", "token1"),
    "uniswap_v3": ("token0", "token1"),
    "aerodrome_v1": ("token0", "token1"),
    "aerodrome_slipstream": ("token0", "token1"),
    "beefy_vault": (),  # Uses want() from vault
    "raydium_amm": ("token0", "token1"),
    "hyperion": ("token0", "token1"),
    "balancer_v3": (),  # Multi-token pools
    "spectra_v2": (),  # Yield tokenization
    "vaultcraft": ("asset",),
    "yield_yak": ("asset",),
    "etherex_cl": ("token0", "token1"),
    "peapods_finance": ("asset",),
}


def _get_adapters_mapping(config: Union[Dict[str, object], object]) -> Dict[str, object]:
    """Return adapters mapping from StrategyConfig or plain dict."""
    if isinstance(config, dict):
        adapters = config.get("adapters", {})
    else:
        adapters = getattr(config, "adapters", {})
    return adapters or {}


def _extract_token_field(value: object, field_name: str) -> Optional[Tuple[str, str]]:
    """Resolve a token field from config, handling ${ENV} placeholders."""
    if value is None:
        return None

    label = field_name
    env_name = None
    resolved = value

    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_name = value[2:-1]
        resolved = os.getenv(env_name, "")
        if env_name:
            label = env_name

    if not isinstance(resolved, str):
        return None

    resolved = resolved.strip()
    if not resolved or not resolved.startswith("0x"):
        return None

    try:
        checksum = Web3.to_checksum_address(resolved) if Web3 is not None else resolved
    except Exception:
        checksum = resolved

    addr_lower = str(checksum).lower()

    if env_name is None and label == field_name:
        for name, env_val in os.environ.items():
            if isinstance(env_val, str) and env_val.lower() == addr_lower:
                label = name
                break

    return addr_lower, label


def adapter_required_tokens(adapter_cfg: Optional[Dict[str, object]]) -> List[Tuple[str, str]]:
    """Return list of (token_address, label) required by an adapter."""
    if not adapter_cfg:
        return []
    adapter_type = str(adapter_cfg.get("type") or "").lower()
    fields: Iterable[str] = REQUIRED_TOKEN_FIELDS.get(adapter_type, ())
    tokens: List[Tuple[str, str]] = []
    for field in fields:
        spec = _extract_token_field(adapter_cfg.get(field), field)
        if spec:
            tokens.append(spec)
    return tokens


def gather_required_token_labels(config: Union[Dict[str, object], object]) -> Dict[str, str]:
    """Gather labels for all tokens required by configured adapters."""
    labels: Dict[str, str] = {}
    adapters = _get_adapters_mapping(config)
    for adapter_cfg in adapters.values():
        for addr, label in adapter_required_tokens(adapter_cfg):
            labels.setdefault(addr, label)
    return labels


def get_adapter_config(config: Union[Dict[str, object], object], pool_id: str) -> Optional[Dict[str, object]]:
    """Return adapter configuration for the given pool id, handling prefixes."""
    adapters = _get_adapters_mapping(config)
    if pool_id in adapters:
        return adapters[pool_id]
    key_with_prefix = pool_id if pool_id.startswith("pool:") else f"pool:{pool_id}"
    if key_with_prefix in adapters:
        return adapters[key_with_prefix]
    key_without_prefix = pool_id[5:] if pool_id.startswith("pool:") else pool_id
    if key_without_prefix in adapters:
        return adapters[key_without_prefix]
    return None


def validate_adapter_coverage(config_path: str) -> int:
    """
    Validate adapter coverage from config file.
    Returns 0 on success, 1 on validation failure.
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config: {e}")
        return 1

    adapters = config.get("adapters", {})
    if not adapters:
        print("❌ No adapters configured")
        return 1

    # EIP-55 address pattern (checksummed Ethereum address)
    address_pattern = re.compile(r'^0x[a-fA-F0-9]{40}$')
    
    missing_vars = []
    invalid_addresses = []
    total_adapters = len(adapters)
    valid_adapters = 0

    for pool_id, adapter_cfg in adapters.items():
        adapter_type = str(adapter_cfg.get("type", "unknown"))
        required_fields = REQUIRED_TOKEN_FIELDS.get(adapter_type, ())
        
        # Also check other required fields like pool, vault, router, market, etc.
        extra_required = []
        if adapter_type == "aave_v3":
            extra_required = ["pool"]
        elif adapter_type in ["erc4626", "yearn"]:
            extra_required = ["vault"]
        elif adapter_type == "lp_beefy_aero":
            extra_required = ["router", "beefy_vault"]
        elif adapter_type == "comet":
            extra_required = ["market"]
        elif adapter_type == "ctoken":
            extra_required = ["ctoken"]
        
        all_required = list(required_fields) + extra_required
        pool_valid = True
        
        for field in all_required:
            value = adapter_cfg.get(field, "")
            
            # Check if it's an env var reference
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                resolved = os.getenv(env_var, "")
                
                if not resolved:
                    missing_vars.append(f"{pool_id}: {env_var} (field: {field})")
                    pool_valid = False
                elif not address_pattern.match(resolved):
                    invalid_addresses.append(f"{pool_id}: {env_var}={resolved} (invalid EIP-55)")
                    pool_valid = False
            elif isinstance(value, str) and value.startswith("0x"):
                # Direct address in config
                if not address_pattern.match(value):
                    invalid_addresses.append(f"{pool_id}: {field}={value} (invalid EIP-55)")
                    pool_valid = False
            else:
                # Required field is missing or empty
                missing_vars.append(f"{pool_id}: {field} (missing or empty)")
                pool_valid = False
        
        if pool_valid:
            valid_adapters += 1

    print("=" * 80)
    print("ADAPTER COVERAGE VALIDATION")
    print("=" * 80)
    print(f"Total adapters: {total_adapters}")
    print(f"Valid adapters: {valid_adapters}")
    print(f"Invalid adapters: {total_adapters - valid_adapters}")
    print()

    if missing_vars:
        print("❌ MISSING ENVIRONMENT VARIABLES:")
        for msg in missing_vars:
            print(f"  • {msg}")
        print()

    if invalid_addresses:
        print("❌ INVALID ADDRESSES (not EIP-55 compliant):")
        for msg in invalid_addresses:
            print(f"  • {msg}")
        print()

    if missing_vars or invalid_addresses:
        print("=" * 80)
        print("❌ VALIDATION FAILED")
        print("=" * 80)
        return 1
    
    print("=" * 80)
    print("✅ VALIDATION PASSED - All adapters have valid configuration")
    print("=" * 80)
    return 0


def main() -> int:
    """CLI entry point for adapter_utils."""
    parser = argparse.ArgumentParser(
        description="Adapter utilities for Wave Rotation strategy"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate adapter coverage and configuration"
    )
    validate_parser.add_argument(
        "--config",
        default="bots/wave_rotation/config.json",
        help="Path to config.json file (default: bots/wave_rotation/config.json)"
    )
    
    args = parser.parse_args()
    
    if args.command == "validate":
        return validate_adapter_coverage(args.config)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
