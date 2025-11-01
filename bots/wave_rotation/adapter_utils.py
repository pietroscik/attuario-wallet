#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Adapter helper utilities shared across strategy components."""

from __future__ import annotations

import os
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
