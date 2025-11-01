"""Adapter registry for portfolio operations."""

from __future__ import annotations

import importlib
import os
from typing import Any, Dict, Tuple, Type

from .base import Adapter


def _missing_adapter_cls(dep_name: str, adapter_name: str, exc: Exception) -> Type[Adapter]:
    class _MissingAdapter(Adapter):  # type: ignore[abstract]
        """Placeholder that surfaces the missing optional dependency at runtime."""

        def __init__(self, *_args, **_kwargs):
            raise ModuleNotFoundError(
                f"{adapter_name} requires optional dependency '{dep_name}'."
            ) from exc

        def deposit_all(self) -> Dict[str, object]:  # pragma: no cover - defensive path
            raise RuntimeError(f"Dependency '{dep_name}' missing for {adapter_name}") from exc

        def withdraw_all(self) -> Dict[str, object]:  # pragma: no cover - defensive path
            raise RuntimeError(f"Dependency '{dep_name}' missing for {adapter_name}") from exc

    _MissingAdapter.__name__ = adapter_name
    return _MissingAdapter


def _load_adapter(module_name: str, class_name: str, dep_hint: str = "web3") -> Type[Adapter]:
    try:
        module = importlib.import_module(f".{module_name}", __name__)
        cls = getattr(module, class_name)
        if not issubclass(cls, Adapter):  # pragma: no cover - defensive check
            raise TypeError(f"{class_name} must extend Adapter")
        return cls
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency path
        missing = exc.name or dep_hint
        return _missing_adapter_cls(missing, class_name, exc)


ADAPTER_TYPES: Dict[str, Type[Adapter]] = {
    "erc4626": _load_adapter("erc4626", "ERC4626Adapter"),
    "aave_v3": _load_adapter("aave_v3", "AaveV3Adapter"),
    "lp_beefy_aero": _load_adapter("lp_beefy_aero", "LpBeefyAerodromeAdapter"),
    "yearn": _load_adapter("yearn", "YearnAdapter"),
    "comet": _load_adapter("comet", "CometAdapter"),
    "ctoken": _load_adapter("ctoken", "CTokenAdapter"),
    # New adapters for 50 asset integration
    "uniswap_v2": _load_adapter("uniswap_v2", "UniswapV2Adapter"),
    "uniswap_v3": _load_adapter("uniswap_v3", "UniswapV3Adapter"),
    "aerodrome_v1": _load_adapter("aerodrome_v1", "AerodromeV1Adapter"),
    "aerodrome_slipstream": _load_adapter("aerodrome_slipstream", "AerodromeSlipstreamAdapter"),
    "beefy_vault": _load_adapter("beefy_vault", "BeefyVaultAdapter"),
    "raydium_amm": _load_adapter("raydium_amm", "RaydiumAmmAdapter"),
    "hyperion": _load_adapter("hyperion", "HyperionAdapter"),
    "balancer_v3": _load_adapter("balancer_v3", "BalancerV3Adapter"),
    "spectra_v2": _load_adapter("spectra_v2", "SpectraV2Adapter"),
    "vaultcraft": _load_adapter("vaultcraft", "VaultcraftAdapter"),
    "yield_yak": _load_adapter("yield_yak", "YieldYakAdapter"),
    "etherex_cl": _load_adapter("etherex_cl", "EtherexCLAdapter"),
    "peapods_finance": _load_adapter("peapods_finance", "PeapodsFinanceAdapter"),
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


def _resolve_pool_key(pool_id: str, adapters: Dict[str, object]) -> str | None:
    """Allow both `pool:<name>` and bare `<name>` adapter identifiers."""
    if pool_id in adapters:
        return pool_id
    if not pool_id.startswith("pool:"):
        prefixed = f"pool:{pool_id}"
        if prefixed in adapters:
            return prefixed
    return None


def get_adapter(pool_id: str, config: Dict[str, object], w3, account) -> Tuple[object, str | None]:
    adapters_cfg = config.get("adapters", {}) or {}
    key = _resolve_pool_key(pool_id, adapters_cfg)
    if key is None:
        return None, f"no_adapter:{pool_id}"

    entry = adapters_cfg[key]
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
