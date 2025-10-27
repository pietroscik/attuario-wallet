"""Adapter registry for portfolio operations."""

from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from .aave_v3 import AaveV3Adapter
from .erc4626 import ERC4626Adapter
from .lp_beefy_aero import LpBeefyAerodromeAdapter


ADAPTER_TYPES = {
    "erc4626": ERC4626Adapter,
    "aave_v3": AaveV3Adapter,
    "lp_beefy_aero": LpBeefyAerodromeAdapter,
}


def _resolve_env(value: Any) -> Any:
    if isinstance(value, str):
        resolved = os.path.expandvars(value)
        if resolved.startswith("${") and resolved.endswith("}"):
            return ""
        if resolved.startswith("$") and "{" not in resolved:
            return ""
        return resolved
    if isinstance(value, dict):
        return {k: _resolve_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env(v) for v in value]
    return value


def get_adapter(pool_id: str, config: Dict[str, object], w3, account) -> Tuple[object, str | None]:
    adapters_cfg = config.get("adapters", {}) or {}
    entry = adapters_cfg.get(pool_id)
    if entry is None:
        return None, f"no_adapter:{pool_id}"

    resolved_entry = _resolve_env(entry)

    adapter_type = str(resolved_entry.get("type", "")).lower()
    cls = ADAPTER_TYPES.get(adapter_type)
    if cls is None:
        return None, f"unknown_type:{adapter_type or 'unset'}"

    try:
        adapter = cls(w3, resolved_entry, account, account.address)
    except Exception as exc:  # pragma: no cover - defensive logging
        return None, f"adapter_init_error:{type(exc).__name__}"
    return adapter, None
