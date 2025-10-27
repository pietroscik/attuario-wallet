#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Portfolio automation: withdraw/deposit via configured adapters."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from adapters import get_adapter
from onchain import get_signer_context
from ops_guard import gas_ceiling_ok, should_move


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _load_config_dict(config_obj) -> Dict[str, object]:
    if isinstance(config_obj, dict):
        return config_obj
    if hasattr(config_obj, "__dict__"):
        return dict(config_obj.__dict__)
    config_path = Path(__file__).resolve().parent / "config.json"
    return json.loads(config_path.read_text())


def _parse_timestamp(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _estimate_move_gas(curr_adapter, next_adapter, w3) -> int:
    total = 0
    try:
        if curr_adapter is not None:
            shares = curr_adapter._max_redeem()
            if shares > 0:
                txw = curr_adapter.vault.functions.redeem(
                    shares, curr_adapter.sender, curr_adapter.sender
                ).build_transaction({"from": curr_adapter.sender})
                total += int(w3.eth.estimate_gas(txw))
    except Exception:
        total = max(total, 280000)

    try:
        if next_adapter is not None:
            balance = next_adapter._asset_balance()
            if balance > 0:
                allowance = next_adapter._allowance()
                if allowance < balance:
                    txa = next_adapter.asset.functions.approve(
                        next_adapter.vault.address, balance
                    ).build_transaction({"from": next_adapter.sender})
                    total += int(w3.eth.estimate_gas(txa))
                txd = next_adapter.vault.functions.deposit(
                    balance, next_adapter.sender
                ).build_transaction({"from": next_adapter.sender})
                total += int(w3.eth.estimate_gas(txd))
    except Exception:
        total = max(total, 450000)

    return max(total, 0)


def rotate_portfolio(
    previous_pool: Optional[str],
    next_pool: Optional[str],
    config,
    capital_eth: float,
    score_best: float,
    score_current: Optional[float],
    last_move_at: Optional[str] = None,
) -> Tuple[str, bool]:
    """Run withdraw/deposit operations according to adapters configuration."""

    if not _env_flag("PORTFOLIO_AUTOMATION_ENABLED", False):
        return "disabled", False

    dry_run = _env_flag("PORTFOLIO_DRY_RUN", False)
    cfg_dict = _load_config_dict(config)

    ctx = get_signer_context()
    if ctx is None:
        return "signer_unavailable", False
    _, w3, account = ctx

    rotated = previous_pool != next_pool

    cooldown_raw = os.getenv("SWITCH_COOLDOWN_S", "0")
    try:
        cooldown_seconds = int(float(cooldown_raw))
    except ValueError:
        cooldown_seconds = 0
    cooldown_seconds = max(0, cooldown_seconds)

    now_utc = datetime.utcnow()
    if (
        cooldown_seconds > 0
        and rotated
        and last_move_at is not None
        and not dry_run
    ):
        last_dt = _parse_timestamp(last_move_at)
        if last_dt is not None:
            elapsed = (now_utc - last_dt).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                return f"skip:cooldown:{remaining}s", False

    adapter_prev = None
    adapter_next = None

    if previous_pool and rotated:
        adapter_prev, err_prev = get_adapter(previous_pool, cfg_dict, w3, account)
        if adapter_prev is None:
            return f"skip:{err_prev}", False

    if next_pool:
        adapter_next, err_next = get_adapter(next_pool, cfg_dict, w3, account)
        if adapter_next is None:
            return f"skip:{err_next}", False

    if adapter_prev is None and adapter_next is None:
        return "noop", False

    gas_ok, gas_note = gas_ceiling_ok(w3)
    if not gas_ok and not dry_run:
        return f"skip:{gas_note}", False

    est_gas = _estimate_move_gas(adapter_prev, adapter_next, w3)
    edge_ok, edge_note = should_move(
        capital_eth,
        score_best,
        score_current if score_current is not None else 0.0,
        est_move_gas=est_gas,
        w3=w3,
    )
    if not edge_ok and not dry_run:
        return f"skip:{edge_note}", False

    notes: list[str] = []
    notes.append(f"guard:{gas_note}")
    notes.append(f"guard:{edge_note}")

    movement = False

    if adapter_prev is not None and rotated:
        if dry_run:
            notes.append(f"withdraw:dry:{previous_pool}")
        else:
            result = adapter_prev.withdraw_all()
            status = result.get("status", "unknown")
            tx_hash = result.get("withdraw_tx")
            if status == "ok" and tx_hash:
                movement = True
            suffix = f":{tx_hash}" if tx_hash else ""
            notes.append(f"withdraw:{status}{suffix}")

    if adapter_next is not None:
        if dry_run:
            pool_label = next_pool or "unknown"
            notes.append(f"deposit:dry:{pool_label}")
        else:
            result = adapter_next.deposit_all()
            status = result.get("status", "unknown")
            if status == "ok":
                txs = []
                if result.get("approve_tx"):
                    txs.append(f"approve={result['approve_tx']}")
                if result.get("deposit_tx"):
                    txs.append(f"deposit={result['deposit_tx']}")
                    movement = True
                suffix = f":{'|'.join(txs)}" if txs else ""
            else:
                suffix = ""
            notes.append(f"deposit:{status}{suffix}")

    status = "|".join(filter(None, notes))
    return status or "noop", movement
