"""Adapter registry for portfolio operations."""

from __future__ import annotations

from typing import Dict, Tuple

from .erc4626 import ERC4626Adapter


ADAPTER_TYPES = {
    "erc4626": ERC4626Adapter,
}


def get_adapter(pool_id: str, config: Dict[str, object], w3, account) -> Tuple[object, str | None]:
    adapters_cfg = config.get("adapters", {}) or {}
    entry = adapters_cfg.get(pool_id)
    if entry is None:
        return None, f"no_adapter:{pool_id}"

    adapter_type = str(entry.get("type", "")).lower()
    cls = ADAPTER_TYPES.get(adapter_type)
    if cls is None:
        return None, f"unknown_type:{adapter_type or 'unset'}"

    adapter = cls(w3, entry, account, account.address)
    return adapter, None
