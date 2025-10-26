#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Execution helpers for Attuario Wave Rotation."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Tuple

from web3 import Web3

from adapters import get_adapter as get_explicit_adapter
from auto_cache import get_cached, set_cached
from auto_registry import pick_auto_adapter, probe_type
from onchain import get_signer_context
from ops_guard import gas_ceiling_ok, should_move


def should_switch(score_new: float, score_old: float, delta: float) -> bool:
    if score_old <= 0:
        return score_new > 0
    # CODEX_RULES: switch if score_new >= score_old * (1 + delta)
    return score_new >= score_old * (1.0 + delta)


def settle_day(capital: float, r_net: float, reinvest_ratio: float) -> Tuple[float, float, float]:
    """Return (profit, new_capital, treasury_delta)."""
    profit = capital * r_net
    capital_new = capital + reinvest_ratio * profit
    treasury_delta = (1.0 - reinvest_ratio) * profit if profit > 0 else 0.0
    return profit, capital_new, treasury_delta


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
STATE_PATH = BASE_DIR / "state.json"


def _load_config_dict() -> dict:
    return json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except json.JSONDecodeError:
        return {}


def _save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2))


def _explicit_adapter(pool_id: str, config: dict, w3, account):
    adapter, err = get_explicit_adapter(pool_id, config, w3, account)
    if adapter is None:
        alt_id = f"pool:{pool_id}" if not pool_id.startswith("pool:") else pool_id[5:]
        if alt_id != pool_id:
            adapter, err = get_explicit_adapter(alt_id, config, w3, account)
        if adapter is None:
            return None, err
    return adapter, "explicit"


def _auto_adapter(
    pool_id: str,
    address: str | None,
    signer,
    sender,
    *,
    w3,
    ttl_hours: float,
) -> tuple[object | None, str]:
    if not address or not isinstance(address, str) or not address.startswith("0x"):
        return None, "none"
    address = Web3.to_checksum_address(address)
    cache_key = f"{pool_id}:{address.lower()}"
    cached = get_cached(cache_key, ttl_hours)
    if cached:
        if cached["type"] == "none":
            return None, "none(cache)"
        ok, adapter_type, cls = probe_type(w3, address)
        if ok:
            adapter = cls(w3, signer, sender, address)
            return adapter, f"auto:{adapter_type}"
        return None, "none(cache_miss)"

    ok, adapter_type, cls = probe_type(w3, address)
    if not ok:
        set_cached(cache_key, None, reason="probe")
        return None, "none"
    adapter = cls(w3, signer, sender, address)
    set_cached(cache_key, adapter_type, reason="probe")
    return adapter, f"auto:{adapter_type}"


def _estimate_movement_gas(current_adapter, next_adapter, w3) -> int:
    total = 0
    try:
        if current_adapter is not None:
            try:
                shares = current_adapter.vault.functions.maxRedeem(current_adapter.sender).call()
                if shares > 0:
                    tx = current_adapter.vault.functions.redeem(
                        shares, current_adapter.sender, current_adapter.sender
                    ).build_transaction({"from": current_adapter.sender})
                    total += int(w3.eth.estimate_gas(tx))
            except Exception:
                total += 280_000
    except AttributeError:
        total += 280_000

    try:
        if next_adapter is not None:
            try:
                tx_deposit = next_adapter.vault.functions.deposit(1, next_adapter.sender).build_transaction(
                    {"from": next_adapter.sender}
                )
                total += int(w3.eth.estimate_gas(tx_deposit))
            except Exception:
                total += 200_000
            total += 60_000  # approve fallback
    except AttributeError:
        total += 200_000

    return max(total, 0)


def move_capital_smart(
    current_pool: str | None,
    next_pool: str | None,
    *,
    current_address: str | None,
    next_address: str | None,
    capital_eth: float,
    score_best: float,
    score_curr: float | None,
    dry_run: bool = False,
) -> str:
    state = _load_state()

    ctx = get_signer_context()
    if ctx is None:
        return "onchain_disabled"
    _, w3, account = ctx

    ok_gas, note_gas = gas_ceiling_ok(w3)
    if not ok_gas:
        return f"SKIP:{note_gas}"

    config = _load_config_dict()
    ttl_hours_raw = os.getenv("ADAPTER_CACHE_TTL_H", "168")
    try:
        ttl_hours = float(ttl_hours_raw)
    except ValueError:
        ttl_hours = 168.0

    current_adapter = None
    current_src = None
    if current_pool:
        current_adapter, current_src = _explicit_adapter(current_pool, config, w3, account)
        if current_adapter is None:
            current_adapter, current_src = _auto_adapter(
                current_pool,
                current_address,
                account,
                account.address,
                w3=w3,
                ttl_hours=ttl_hours,
            )

    next_adapter = None
    next_src = None
    if next_pool:
        next_adapter, next_src = _explicit_adapter(next_pool, config, w3, account)
        if next_adapter is None:
            next_adapter, next_src = _auto_adapter(
                next_pool,
                next_address,
                account,
                account.address,
                w3=w3,
                ttl_hours=ttl_hours,
            )

    if current_adapter is None and next_adapter is None:
        return "SKIP:no_adapters"

    estimate_gas = _estimate_movement_gas(current_adapter, next_adapter, w3)
    cooldown_raw = os.getenv("SWITCH_COOLDOWN_S", "0")
    try:
        cooldown_seconds = int(float(cooldown_raw))
    except ValueError:
        cooldown_seconds = 0
    cooldown_seconds = max(0, cooldown_seconds)

    if (
        cooldown_seconds > 0
        and not dry_run
        and current_pool != next_pool
        and state.get("last_portfolio_move")
    ):
        try:
            last_ts = time.strptime(state["last_portfolio_move"], "%Y-%m-%d %H:%M:%S")
            last_epoch = time.mktime(last_ts)
        except (ValueError, OverflowError):
            last_epoch = None
        if last_epoch is not None:
            elapsed = time.time() - last_epoch
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                return f"SKIP:cooldown:{remaining}s"

    ok_edge, note_edge = should_move(
        capital_eth,
        score_best,
        score_curr or 0.0,
        est_move_gas=estimate_gas,
        w3=w3,
    )
    if not ok_edge:
        return f"SKIP:{note_edge}"

    notes: list[str] = [f"guard:{note_gas}", f"guard:{note_edge}"]
    movement = False

    if current_pool and next_pool and current_pool != next_pool and current_adapter is not None:
        if dry_run:
            notes.append(f"withdraw:dry:{current_pool}")
        else:
            res = current_adapter.withdraw_all()
            status = res.get("status", "unknown")
            tx_hash = res.get("withdraw_tx")
            if status == "ok" and tx_hash:
                movement = True
            suffix = f":{tx_hash}" if tx_hash else ""
            notes.append(f"withdraw:{status}{suffix}")

    if next_pool and next_adapter is not None:
        if dry_run:
            notes.append(f"deposit:dry:{next_pool}")
        else:
            res = next_adapter.deposit_all()
            status = res.get("status", "unknown")
            txs = []
            if res.get("approve_tx"):
                txs.append(f"approve={res['approve_tx']}")
            if res.get("deposit_tx"):
                txs.append(f"deposit={res['deposit_tx']}")
                movement = True
            suffix = f":{'|'.join(txs)}" if txs else ""
            notes.append(f"deposit:{status}{suffix}")

    sources = f"curr={current_src or '-'};next={next_src or '-'};gas={estimate_gas}"

    if movement and not dry_run:
        state["last_portfolio_move"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        _save_state(state)

    return "|".join(notes) + f"|{sources}"
