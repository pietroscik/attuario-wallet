#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Attuario Wave Rotation – strategia giornaliera

Caratteristiche:
  • Fetch multi-chain (DeFiLlama + eventuali API specifiche)
  • Score = r / (1 + c⋅(1−ρ))
  • Switch se Δscore ≥ 1%
  • Reinvest 50% del profitto, 50% in treasury (USDC)
  • Stop-loss giornaliero -10%, take-profit nessuna azione extra
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

import requests
from dotenv import load_dotenv

from auto_cache import get_cached, set_cached
from auto_registry import probe_type
from data_sources import fetch_pools_scoped
from executor import move_capital_smart, settle_day
from logger import append_log, build_telegram_message, timestamp_now
from onchain import (
    push_strategy_update,
    update_active_pool,
    resume_vault,
    get_available_capital_eth,
    get_signer_context,
)
from scoring import daily_rate, normalized_score, should_switch
from treasury import dispatch_treasury_payout

BASE_DIR = Path(__file__).resolve().parent
CAPITAL_FILE = BASE_DIR / "capital.txt"
TREASURY_FILE = BASE_DIR / "treasury.txt"
STATE_FILE = BASE_DIR / "state.json"
LOG_FILE = BASE_DIR / "log.csv"


def parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


@dataclass
class StrategyConfig:
    chains: List[str]
    min_tvl_usd: float
    delta_switch: float
    reinvest_ratio: float
    treasury_token: str
    schedule_utc: str
    stop_loss_daily: float
    take_profit_daily: float
    sources: Dict[str, object]
    vault: Dict[str, str]
    telegram: Dict[str, object]
    adapters: Dict[str, object]
    selection: Dict[str, object]
    autopause: Dict[str, object]

    @staticmethod
    def load(path: Path) -> "StrategyConfig":
        with path.open() as fh:
            raw = json.load(fh)
        return StrategyConfig(
            chains=raw.get("chains", []),
            min_tvl_usd=float(raw.get("min_tvl_usd", 0)),
            delta_switch=float(raw.get("delta_switch", 0.01)),
            reinvest_ratio=float(raw.get("reinvest_ratio", 0.5)),
            treasury_token=raw.get("treasury_token", "USDC"),
            schedule_utc=raw.get("schedule_utc", "07:00"),
            stop_loss_daily=float(raw.get("stop_loss_daily", -0.10)),
            take_profit_daily=float(raw.get("take_profit_daily", 0.05)),
            sources=raw.get("sources", {}),
            vault=raw.get("vault", {}),
            telegram=raw.get("telegram", {}),
            adapters=raw.get("adapters", {}),
            selection=raw.get("selection", {}),
            autopause=raw.get("autopause", {}),
        )


@dataclass
class StrategyState:
    pool_id: Optional[str] = None
    pool_name: Optional[str] = None
    chain: Optional[str] = None
    score: float = 0.0
    updated_at: Optional[str] = None
    crisis_streak: int = 0
    last_crisis_at: Optional[str] = None
    paused: bool = False
    day_utc: Optional[str] = None
    capital_start_day: float = 0.0
    last_resume_attempt: Optional[str] = None
    last_portfolio_move: Optional[str] = None
    last_switch_ts: Optional[float] = None

    @staticmethod
    def load(path: Path) -> "StrategyState":
        if not path.exists():
            return StrategyState()
        with path.open() as fh:
            raw = json.load(fh)
        return StrategyState(
            pool_id=raw.get("pool_id"),
            pool_name=raw.get("pool_name"),
            chain=raw.get("chain"),
            score=float(raw.get("score", 0.0)),
            updated_at=raw.get("updated_at"),
            crisis_streak=int(raw.get("crisis_streak", 0) or 0),
            last_crisis_at=raw.get("last_crisis_at"),
            paused=bool(raw.get("paused", False)),
            day_utc=raw.get("day_utc"),
            capital_start_day=float(raw.get("capital_start_day", 0.0)),
            last_resume_attempt=raw.get("last_resume_attempt"),
            last_portfolio_move=raw.get("last_portfolio_move"),
            last_switch_ts=float(raw.get("last_switch_ts")) if raw.get("last_switch_ts") is not None else None,
        )

    def save(self, path: Path) -> None:
        payload = {
            "pool_id": self.pool_id,
            "pool_name": self.pool_name,
            "chain": self.chain,
            "score": self.score,
            "updated_at": self.updated_at,
            "crisis_streak": self.crisis_streak,
            "last_crisis_at": self.last_crisis_at,
            "paused": self.paused,
            "day_utc": self.day_utc,
            "capital_start_day": self.capital_start_day,
            "last_resume_attempt": self.last_resume_attempt,
            "last_portfolio_move": self.last_portfolio_move,
            "last_switch_ts": self.last_switch_ts,
        }
        with path.open("w") as fh:
            json.dump(payload, fh, indent=2)


def load_decimal_file(path: Path, default: float) -> float:
    if not path.exists():
        return default
    try:
        with path.open() as fh:
            return float(Decimal(fh.read().strip()))
    except (InvalidOperation, ValueError):
        return default


def store_decimal_file(path: Path, value: float) -> None:
    path.write_text(f"{value:.6f}")


def send_telegram(msg: str, config: StrategyConfig) -> None:
    tg_conf = config.telegram or {}
    if not tg_conf.get("enabled", False):
        return

    token = os.getenv(str(tg_conf.get("bot_token_env", "")) or "")
    chat_id = os.getenv(str(tg_conf.get("chat_id_env", "")) or "")
    if not token or not chat_id:
        print("[telegram] skipped: token/chat_id missing")
        return
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/sendMessage",
            params={"chat_id": chat_id, "text": msg},
            timeout=10,
        )
        if not r.ok:
            print(f"[telegram] error: {r.text}")
    except Exception as exc:  # pragma: no cover - network failure path
        print(f"[telegram] exception: {exc}")


class AdapterInfo(NamedTuple):
    ok: bool
    source: str
    adapter_type: Optional[str] = None


def select_best_pool(
    pools: List[Dict[str, float]],
    config: StrategyConfig,
    state: StrategyState,
    w3,
    _capital_hint_eth: float,
) -> Tuple[Dict[str, object] | None, Dict[str, Dict[str, object]]]:
    adapters_cfg = config.adapters or {}
    selection_cfg = config.selection or {}
    blacklist_projects = {
        str(p).lower() for p in selection_cfg.get("blacklist_projects", []) if p
    }

    def safe_float(value: object, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    exclude_virtual = os.getenv("EXCLUDE_VIRTUAL", "0").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    require_adapter = os.getenv("REQUIRE_ADAPTER_BEFORE_RANK", "0").strip().lower() in {
        "1",
        "true",
        "yes",
    }

    ttl_raw = os.getenv("ADAPTER_CACHE_TTL_H", "168")
    try:
        ttl_hours = float(ttl_raw)
    except ValueError:
        ttl_hours = 168.0

    builtin_adapter_hints = [
        ("beefy", ("BEEFY", "beefy-auto")),
        ("yearn", ("YEARN", "yearn-vault")),
        ("sonne", ("CTOKEN", "compound-like")),
        ("moonwell", ("CTOKEN", "compound-like")),
        ("compound", ("CTOKEN", "compound")),
        ("venus", ("CTOKEN", "compound-like")),
        ("lodestar", ("CTOKEN", "compound-like")),
        ("morpho", ("CTOKEN", "compound-like")),
        ("comet", ("COMET", "compound-iii")),
        ("exactly", ("ERC4626", "erc4626-vault")),
        ("midas", ("ERC4626", "erc4626-vault")),
        ("gearbox", ("ERC4626", "erc4626-vault")),
        ("aave", ("AAVEV3", "aave-like")),
        ("spark", ("AAVEV3", "aave-like")),
        ("radiant", ("AAVEV3", "aave-like")),
        ("geist", ("AAVEV3", "aave-like")),
        ("benqi", ("AAVEV3", "aave-like")),
    ]

    adapter_meta: Dict[str, AdapterInfo] = {}

    def _pool_meta_key(pool: Dict[str, object]) -> str:
        pool_id = str(pool.get("pool_id") or "").strip()
        if pool_id:
            return pool_id
        address = str(pool.get("address") or "").strip().lower()
        if address:
            return f"addr:{address}"
        project = str(pool.get("project") or "").strip().lower()
        chain = str(pool.get("chain") or "").strip().lower()
        if project and chain:
            return f"{chain}:{project}:{id(pool)}"
        return f"pool:{id(pool)}"

    def resolve_adapter(pool: Dict[str, object], *, require_probe: bool) -> AdapterInfo:
        key = _pool_meta_key(pool)
        cached_local = adapter_meta.get(key)
        if cached_local and (cached_local.ok or not require_probe):
            return cached_local

        pool_id = str(pool.get("pool_id") or "").strip()
        project = str(pool.get("project") or "").strip().lower()
        chain = str(pool.get("chain") or "").strip().lower()
        address = str(pool.get("address") or "").strip()

        config_keys = []
        if pool_id:
            config_keys.extend([pool_id, f"pool:{pool_id}"])
        if address:
            address_lower = address.lower()
            config_keys.extend([address_lower, f"address:{address_lower}"])
        if project:
            config_keys.extend([project, f"project:{project}"])
        if chain and project:
            config_keys.extend([f"{chain}:{project}", f"project:{project}@{chain}"])

        for cfg_key in config_keys:
            if not cfg_key:
                continue
            if cfg_key in adapters_cfg:
                adapter_hint = adapters_cfg[cfg_key]
                if isinstance(adapter_hint, dict):
                    adapter_type = adapter_hint.get("type") or adapter_hint.get("adapter")
                    tag = adapter_hint.get("source") or adapter_hint.get("label") or "config"
                elif isinstance(adapter_hint, str):
                    adapter_type = adapter_hint
                    tag = adapter_hint
                elif adapter_hint:
                    adapter_type = str(adapter_hint)
                    tag = "config"
                else:
                    adapter_type = None
                    tag = "config"
                info = AdapterInfo(True, f"config:{tag}", adapter_type if adapter_type else None)
                adapter_meta[key] = info
                return info

        normalized_project = re.sub(r"[^a-z0-9]+", "", project)
        for hint, (adapter_type, label) in builtin_adapter_hints:
            if hint in normalized_project:
                info = AdapterInfo(True, f"builtin:{label}", adapter_type)
                adapter_meta[key] = info
                cache_key = None
                if pool_id and address:
                    cache_key = f"{pool_id}:{address.lower()}"
                elif address:
                    cache_key = address.lower()
                elif pool_id:
                    cache_key = pool_id
                if cache_key:
                    set_cached(cache_key, adapter_type, reason=info.source)
                return info

        cache_key = None
        if pool_id and address:
            cache_key = f"{pool_id}:{address.lower()}"
        elif address:
            cache_key = address.lower()
        elif pool_id:
            cache_key = pool_id

        if cache_key:
            cached = get_cached(cache_key, ttl_hours)
            if cached:
                adapter_type = cached.get("type")
                reason = cached.get("reason") or "cache"
                if adapter_type and adapter_type != "none":
                    info = AdapterInfo(True, reason, adapter_type)
                    adapter_meta[key] = info
                    return info
                if not require_probe:
                    info = AdapterInfo(False, reason, None)
                    adapter_meta[key] = info
                    return info

        if not address or not address.startswith("0x"):
            info = AdapterInfo(False, "missing_address", None)
            adapter_meta[key] = info
            return info

        if not w3:
            info = AdapterInfo(False, "no_web3", None)
            adapter_meta[key] = info
            return info

        ok, adapter_type, _ = probe_type(w3, address)
        info: AdapterInfo
        if ok:
            info = AdapterInfo(True, f"probe:{adapter_type}", adapter_type)
            if cache_key:
                set_cached(cache_key, adapter_type, reason=info.source)
        else:
            info = AdapterInfo(False, "probe:none", None)
            if cache_key:
                set_cached(cache_key, None, reason=info.source)
        adapter_meta[key] = info
        return info

    def is_virtual(pool: Dict[str, object]) -> bool:
        symbol = str(pool.get("symbol") or "").upper()
        name = str(pool.get("name") or "").upper()
        pool_id = str(pool.get("pool_id") or "").lower()
        return symbol.startswith("VIRTUAL") or "VIRTUAL" in name or "virtual" in pool_id

    def pool_tvl(pool: Dict[str, object]) -> float:
        value = pool.get("tvl_usd")
        if value is None:
            value = pool.get("tvlUsd")
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def pool_staleness(pool: Dict[str, object]) -> float:
        for key in ("apy_age_min", "apyAgeMin", "updatedMin"):
            value = pool.get(key)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
        return 0.0

    def pool_age(pool: Dict[str, object]) -> float:
        for key in ("poolAgeDays", "pool_age_days"):
            value = pool.get(key)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
        return 0.0

    candidates: List[Dict[str, object]] = []
    base_pool_set: List[Dict[str, object]] = []
    base_relaxed = False

    # Apply selection filters from config
    for pool in pools:
        project = str(pool.get("project") or "").lower()
        if project and project in blacklist_projects:
            continue

        # Check virtual tokens
        if exclude_virtual and is_virtual(pool):
            continue

        base_pool_set.append(pool)

    if not base_pool_set and pools:
        base_pool_set = list(pools)
        base_relaxed = True

    survivors: List[Dict[str, object]] = list(base_pool_set)
    filter_report: Dict[str, List[Dict[str, object]]] = {
        "applied": [],
        "skipped": [],
    }

    if base_relaxed:
        filter_report.setdefault("relaxed", []).append("prefilter")

    def apply_filter(tag: str, predicate):
        nonlocal survivors
        if not survivors:
            return

        filtered: List[Dict[str, object]] = []
        rejected_reasons: Counter[str] = Counter()

        for pool in survivors:
            keep, reason = predicate(pool)
            if keep:
                filtered.append(pool)
            else:
                if reason:
                    rejected_reasons[reason] += 1

        if filtered:
            survivors = filtered
            filter_report["applied"].append(
                {
                    "filter": tag,
                    "remaining": len(filtered),
                    "rejections": dict(rejected_reasons),
                }
            )
        else:
            filter_report["skipped"].append(
                {
                    "filter": tag,
                    "reason": dict(rejected_reasons) or {"cause": "all_rejected"},
                }
            )

    def adapter_predicate(pool: Dict[str, object]) -> Tuple[bool, str]:
        info = resolve_adapter(pool, require_probe=require_adapter)
        if info.ok or not require_adapter:
            return True, ""
        reason = info.source or "no_adapter"
        return False, reason

    apply_filter("adapter", adapter_predicate)

    min_tvl = float(config.min_tvl_usd)

    def tvl_predicate(pool: Dict[str, object]) -> Tuple[bool, str]:
        value = pool_tvl(pool)
        if value >= min_tvl:
            return True, ""
        return False, "tvl<min"

    apply_filter("tvl", tvl_predicate)

    if not survivors:
        survivors = list(base_pool_set)
        filter_report["skipped"].append(
            {
                "filter": "fallback",
                "reason": "no_survivors_after_filters",
            }
        )

    if filter_report["skipped"]:
        details: List[str] = []
        for item in filter_report["skipped"]:
            reason = item.get("reason")
            if isinstance(reason, dict):
                reason_desc = ",".join(f"{k}:{v}" for k, v in reason.items())
            else:
                reason_desc = str(reason)
            details.append(f"{item['filter']}->{reason_desc}")
        if details:
            print(f"[select] filtri allentati: {'; '.join(details)}")

    for pool in survivors:
        apy = max(0.0, safe_float(pool.get("apy"), 0.0))
        r_day = daily_rate(apy)

        # CRITICAL FIX: Convert annual fee to daily fee before subtracting
        # fee_pct is annual, need to scale to daily: annual_fee / 365
        cost_annual = max(0.0, safe_float(pool.get("fee_pct"), 0.0))
        cost_daily = cost_annual / 365.0

        risk = max(0.0, min(1.0, safe_float(pool.get("risk_score", 0.0), 0.0)))
        # Use daily cost in score calculation
        s = r_day / (1.0 + cost_daily * (1.0 - risk)) if r_day > 0 else r_day
        r_net = r_day - cost_daily

        adapter_info = resolve_adapter(pool, require_probe=False)

        tvl_value = pool_tvl(pool)
        staleness_value = pool_staleness(pool)
        age_value = pool_age(pool)

        candidate = dict(pool)
        candidate.update(
            {
                "apy": apy,
                "r_day": r_day,
                "r_net": r_net,
                "score": s,
                "cost_daily": cost_daily,
                "cost_annual": cost_annual,
                "adapter_ok": adapter_info.ok,
                "tvl_usd": tvl_value,
                "apy_age_min": staleness_value,
                "pool_age_days": age_value,
            }
        )
        if adapter_info.ok and adapter_info.source:
            candidate["adapter_source"] = adapter_info.source
        if adapter_info.adapter_type:
            candidate["adapter_type"] = adapter_info.adapter_type
        candidates.append(candidate)

    relaxed_notes: List[str] = []

    if not candidates and pools:
        for pool in pools:
            apy = max(0.0, safe_float(pool.get("apy"), 0.0))
            r_day = daily_rate(apy)
            cost_annual = max(0.0, safe_float(pool.get("fee_pct"), 0.0))
            cost_daily = cost_annual / 365.0
            risk = max(0.0, min(1.0, safe_float(pool.get("risk_score", 0.0), 0.0)))
            s = r_day / (1.0 + cost_daily * (1.0 - risk)) if r_day > 0 else r_day
            r_net = r_day - cost_daily
            adapter_info = resolve_adapter(pool, require_probe=False)
            candidate = dict(pool)
            candidate.update(
                {
                    "apy": apy,
                    "r_day": r_day,
                    "r_net": r_net,
                    "score": s,
                    "cost_daily": cost_daily,
                    "cost_annual": cost_annual,
                    "adapter_ok": adapter_info.ok,
                    "tvl_usd": pool_tvl(pool),
                    "apy_age_min": pool_staleness(pool),
                    "pool_age_days": pool_age(pool),
                }
            )
            if adapter_info.ok and adapter_info.source:
                candidate["adapter_source"] = adapter_info.source
            if adapter_info.adapter_type:
                candidate["adapter_type"] = adapter_info.adapter_type
            candidates.append(candidate)
        if candidates:
            relaxed_notes.append("raw_pool")

    if not candidates:
        top_n = int(selection_cfg.get("top_n_scan", int(os.getenv("AUTO_TOP_N", "40")) or 40))
        diagnostics: List[str] = []
        for pool in sorted(pools, key=lambda x: safe_float(x.get("apy"), 0.0), reverse=True)[:top_n]:
            reasons: List[str] = []
            project = str(pool.get("project") or "").lower()
            if project and project in blacklist_projects:
                reasons.append("blacklist")
            if exclude_virtual and is_virtual(pool):
                reasons.append("virtual")
            if require_adapter:
                adapter_info = resolve_adapter(pool, require_probe=require_adapter)
                if not adapter_info.ok:
                    reasons.append(adapter_info.source or "no_adapter")
            if safe_float(pool.get("tvl_usd"), 0.0) < config.min_tvl_usd:
                reasons.append("tvl<min")
            if not reasons:
                reasons.append("other_filters")
            diagnostics.append(f"{pool.get('pool_id','?')}@{pool.get('chain','?')}:" + ",".join(reasons))
            if len(diagnostics) >= 10:
                break
        if diagnostics:
            print("[select] nessun candidato: ", "; ".join(diagnostics))
        return None, {"__diagnostics__": diagnostics}

    ranking_candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)

    adapter_focused = ranking_candidates
    if require_adapter:
        adapter_ready = [c for c in ranking_candidates if c.get("adapter_ok")]
        if adapter_ready:
            adapter_focused = adapter_ready
        else:
            relaxed_notes.append("adapter")

    tvl_ready = [c for c in adapter_focused if safe_float(c.get("tvl_usd"), 0.0) >= min_tvl]
    if tvl_ready:
        adapter_focused = tvl_ready
    elif min_tvl > 0:
        relaxed_notes.append("tvl")

    ranking_candidates = sorted(adapter_focused, key=lambda x: x["score"], reverse=True)
    best = ranking_candidates[0]

    lookup = {c["pool_id"]: c for c in candidates}
    lookup["__filter_report__"] = filter_report
    if relaxed_notes:
        filter_report.setdefault("relaxed", []).extend(relaxed_notes)
        lookup["__relaxed__"] = relaxed_notes
    current = lookup.get(state.pool_id) if state.pool_id else None

    min_delta = float(config.delta_switch)
    cooldown_s = int(selection_cfg.get("switch_cooldown_s", 0) or 0)

    if should_switch(best, current, min_delta=min_delta, cooldown_s=cooldown_s, last_switch_ts=state.last_switch_ts):
        return best, lookup

    return current or best, lookup


def push_onchain(selected: Dict[str, object], capital_token: float) -> Optional[str]:
    pool_name = selected["name"]
    apy_decimal = float(selected["apy"])
    # convert to percent
    apy_percent = apy_decimal * 100.0
    return push_strategy_update(pool_name, apy_percent, capital_token)


def main() -> None:
    load_dotenv()

    config = StrategyConfig.load(BASE_DIR / "config.json")
    state = StrategyState.load(STATE_FILE)
    interval_seconds_env = os.getenv("WAVE_LOOP_INTERVAL_SECONDS")
    try:
        interval_seconds = int(interval_seconds_env) if interval_seconds_env else 3600
    except ValueError:
        interval_seconds = 3600
    interval_seconds = max(300, interval_seconds)
    if interval_seconds % 3600 == 0:
        hours = interval_seconds // 3600
        interval_desc = f"{hours} h"
    elif interval_seconds % 60 == 0:
        minutes = interval_seconds // 60
        interval_desc = f"{minutes} min"
    else:
        interval_desc = f"{interval_seconds} sec"
    interval_factor = interval_seconds / 86400.0

    signer_ctx = get_signer_context()
    w3 = signer_ctx[1] if signer_ctx else None

    config_dict = {
        "chains": config.chains,
        "sources": config.sources,
        "search_scope": os.getenv("SEARCH_SCOPE", config.selection.get("search_scope", "GLOBAL")),
    }

    pools, source_name, stats = fetch_pools_scoped(config_dict)
    if not pools:
        msg = "⚠️ Nessun pool disponibile oggi (fonti vuote)."
        print(msg)
        send_telegram(msg, config)
        return

    capital_hint_eth = load_decimal_file(CAPITAL_FILE, 100.0)

    selected, candidate_map = select_best_pool(pools, config, state, w3, capital_hint_eth)
    if not selected:
        diagnostics = candidate_map.get("__diagnostics__") if candidate_map else None
        detail = ""
        if diagnostics:
            detail = "\n🔍 Dettagli: " + "; ".join(diagnostics)
        msg = "⚠️ Nessun pool supera i vincoli minimi (TVL, dati)." + detail
        print(msg)
        send_telegram(msg, config)
        return

    metadata_bits = [
        f"scope={config_dict['search_scope']}",
        f"source={source_name}",
        f"scan={stats.get('count', '?')}",
    ]
    metadata_bits.append(f"best={selected.get('pool_id')}")
    metadata_bits.append(f"score_best={selected.get('score', 0.0):.6f}")

    relaxed_markers = candidate_map.get("__relaxed__") if candidate_map else None
    if relaxed_markers:
        metadata_bits.append("relaxed=" + "+".join(sorted(set(relaxed_markers))))

    reserve_eth = float(os.getenv("GAS_RESERVE_ETH", "0.004"))
    available_onchain = get_available_capital_eth(reserve_eth)
    gas_status_note: Optional[str] = None
    if available_onchain is not None:
        if available_onchain <= 0:
            gas_status_note = "gas:insufficient"
        elif available_onchain < reserve_eth:
            gas_status_note = "gas:low"

    capital_before = capital_hint_eth
    treasury_total = load_decimal_file(TREASURY_FILE, 0.0)

    current_day = datetime.utcnow().strftime("%Y-%m-%d")
    if state.day_utc != current_day or state.capital_start_day <= 0:
        state.day_utc = current_day
        state.capital_start_day = capital_before if capital_before > 0 else 1.0

    capital_start_day = state.capital_start_day if state.capital_start_day > 0 else 1.0

    selection_cfg = config.selection or {}
    if selection_cfg.get("gas_horizon_h") is not None:
        os.environ["EDGE_HORIZON_H"] = str(selection_cfg.get("gas_horizon_h"))

    previous_pool_id = state.pool_id
    next_pool_id = selected.get("pool_id")
    rotated = previous_pool_id != next_pool_id

    previous_candidate = candidate_map.get(previous_pool_id) if previous_pool_id else None
    previous_score = float((previous_candidate or {}).get("score", state.score or 0.0))
    previous_address = (previous_candidate or {}).get("address")
    next_address = selected.get("address")

    dry_run_enabled = os.getenv("PORTFOLIO_DRY_RUN", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    portfolio_status = move_capital_smart(
        previous_pool_id,
        next_pool_id,
        current_address=previous_address,
        next_address=next_address,
        capital_eth=capital_before,
        score_best=float(selected.get("score", 0.0)),
        score_curr=float((previous_candidate or {}).get("score", state.score or 0.0)),
        dry_run=dry_run_enabled,
    )

    active_pool = selected
    active_pool_id = next_pool_id

    if portfolio_status.startswith("SKIP"):
        active_pool_id = previous_pool_id
        if previous_pool_id and previous_pool_id in candidate_map:
            active_pool = candidate_map[previous_pool_id]
        elif previous_candidate is not None:
            active_pool = previous_candidate

    rotated_effective = active_pool_id != previous_pool_id

    if rotated_effective and not portfolio_status.startswith("SKIP"):
        state.last_switch_ts = time.time()

    if STATE_FILE.exists():
        try:
            latest_state = json.loads(STATE_FILE.read_text())
            state.last_portfolio_move = latest_state.get("last_portfolio_move", state.last_portfolio_move)
        except json.JSONDecodeError:
            pass

    working_pool = active_pool or selected
    metadata_bits.append(f"active={working_pool.get('pool_id')}")
    metadata_bits.append(f"score_active={working_pool.get('score', 0.0):.6f}")

    r_net_daily = working_pool["r_net"]
    r_net_interval = (1.0 + r_net_daily) ** interval_factor - 1.0
    status_head = "executed"
    status_notes: List[str] = []
    extra_notifications: List[str] = []
    if gas_status_note:
        status_notes.append(gas_status_note)
    adapter_source = working_pool.get("adapter_source")
    if adapter_source:
        status_notes.append(f"adapter:{adapter_source}")
    if portfolio_status:
        status_notes.append(f"portfolio:{portfolio_status}")
    if active_pool_id and active_pool_id != next_pool_id:
        status_notes.append(f"target:{next_pool_id or '-'}")

    autopause_cfg = config.autopause or {}
    autopause_streak = int(float(autopause_cfg.get("streak", 3) or 0))
    autopause_streak = max(0, autopause_streak)
    resume_wait_minutes = float(autopause_cfg.get("resume_wait_minutes", 360) or 0)
    resume_wait_minutes = max(0.0, resume_wait_minutes)
    resume_cooldown_minutes = float(autopause_cfg.get("resume_cooldown_minutes", 5) or 0)
    resume_cooldown_minutes = max(0.0, resume_cooldown_minutes)
    fast_signal_min = float(autopause_cfg.get("fast_signal_min", 0.0) or 0.0)

    stop_loss_interval = config.stop_loss_daily * interval_factor
    crisis_flag = r_net_interval < stop_loss_interval

    if crisis_flag:
        state.crisis_streak += 1
        state.last_crisis_at = timestamp_now()
    else:
        state.crisis_streak = 0

    autopause_triggered = False
    if (
        autopause_streak > 0
        and crisis_flag
        and state.crisis_streak >= autopause_streak
        and not state.paused
    ):
        state.paused = True
        state.last_resume_attempt = None
        autopause_triggered = True
        status_notes.append("paused:auto")

    pool_tx = update_active_pool(working_pool["name"], crisis_flag)
    if pool_tx:
        status_notes.append(f"pool:{pool_tx}")

    resume_threshold = timedelta(minutes=resume_wait_minutes) if resume_wait_minutes > 0 else timedelta(0)
    cooldown_resume = (
        timedelta(minutes=resume_cooldown_minutes)
        if resume_cooldown_minutes > 0
        else timedelta(0)
    )

    if state.paused and not crisis_flag and not autopause_triggered:
        now_dt = datetime.utcnow()
        last_crisis_dt = parse_dt(state.last_crisis_at)
        last_resume_dt = parse_dt(state.last_resume_attempt)
        cooldown_ok = (
            last_resume_dt is None
            or cooldown_resume == timedelta(0)
            or now_dt - last_resume_dt >= cooldown_resume
        )
        fast_signal = r_net_interval >= fast_signal_min
        ready_by_time = (
            resume_threshold == timedelta(0)
            or (
                last_crisis_dt is not None
                and now_dt - last_crisis_dt >= resume_threshold
            )
        )

        if cooldown_ok and (fast_signal or ready_by_time):
            resume_tx = resume_vault()
            state.last_resume_attempt = timestamp_now()
            if resume_tx:
                state.paused = False
                state.crisis_streak = 0
                status_notes.append(f"resume:{resume_tx}")
                extra_notifications.append(
                    "✅ Ripresa automatica – vault resume eseguito.\n"
                    f"🔄 tx: {resume_tx}"
                )
            else:
                extra_notifications.append(
                    "⚠️ Tentativo di resume automatico fallito – controlla manualmente."
                )
        elif fast_signal and not cooldown_ok:
            status_notes.append("resume:cooldown")

    capital_after: float
    treasury_delta: float

    if crisis_flag:
        status_head = "stopped"
        capital_after = capital_before
        treasury_delta = 0.0
        print(
            "[stop-loss] r_net_interval="
            f"{r_net_interval:.4%} (threshold {stop_loss_interval:.4%}), capitale invariato."
        )
    elif state.paused:
        status_head = "paused-eval"
        capital_after = capital_before
        treasury_delta = 0.0
        status_notes.append("paused:evaluation")
        print(
            "[paused] stop-loss attivo: sola valutazione, capitale invariato."
        )
    else:
        profit, capital_after, treasury_delta_planned = settle_day(
            capital_before, r_net_interval, config.reinvest_ratio
        )
        store_decimal_file(CAPITAL_FILE, capital_after)

        treasury_delta_effective = 0.0
        treasury_dispatch = None
        if treasury_delta_planned > 0:
            treasury_dispatch = dispatch_treasury_payout(treasury_delta_planned)
            if treasury_dispatch is None:
                treasury_delta_effective = treasury_delta_planned
                status_notes.append("treasury:disabled")
            elif treasury_dispatch.get("eurc_amount"):
                treasury_delta_effective = treasury_delta_planned
                status_notes.append(f"treasury_swap:{treasury_dispatch['swap_tx']}")
                status_notes.append(f"treasury_transfer:{treasury_dispatch['transfer_tx']}")
                extra_notifications.append(
                    "🏦 Treasury aggiornato on-chain.\n"
                    f"↪️ EURC inviati: {treasury_dispatch['eurc_amount']:.2f}\n"
                    f"🔗 tx swap: {treasury_dispatch['swap_tx']}\n"
                    f"🔗 tx transfer: {treasury_dispatch['transfer_tx']}"
                )
            elif treasury_dispatch.get("swap_tx"):
                status_notes.append(f"treasury_swap:{treasury_dispatch['swap_tx']}")
                status_notes.append("treasury:pending")
            else:
                status_notes.append("treasury:skipped")

        treasury_total += treasury_delta_effective
        store_decimal_file(TREASURY_FILE, treasury_total)

        treasury_delta = treasury_delta_effective

        tx_hash = push_onchain(working_pool, capital_after)
        if tx_hash:
            status_notes.append(f"onchain:{tx_hash}")
            print(f"[onchain] executeStrategy → {tx_hash}")

    if autopause_triggered:
        extra_notifications.append(
            "🚨 Crisi prolungata – vault in pausa automatica.\n"
            f"💰 Capitale preservato: {capital_after:.6f} (unità base)\n"
            "💤 Il bot continua la valutazione ogni finestra."
        )

    state.pool_id = active_pool_id or working_pool.get("pool_id")
    state.pool_name = working_pool["name"]
    state.chain = working_pool["chain"]
    state.score = working_pool["score"]
    state.updated_at = timestamp_now()
    state.save(STATE_FILE)

    status_tags = status_notes + metadata_bits
    status_combined = status_head
    if status_tags:
        suffix = "|".join(status_tags)
        status_combined = f"{status_head}|{suffix}" if status_head else suffix

    realized_return = 0.0
    if capital_before > 0:
        realized_return = (capital_after / capital_before) - 1.0

    pnl_daily = capital_after - capital_start_day
    roi_daily_pct = (pnl_daily / capital_start_day) * 100 if capital_start_day else 0.0

    row = {
        "date": timestamp_now(),
        "pool": working_pool["name"],
        "chain": working_pool["chain"],
        "apy": f"{working_pool['apy']:.6f}",
        "r_day": f"{working_pool['r_day']:.6f}",
        "r_net_daily": f"{r_net_daily:.6f}",
        "r_net_interval": f"{r_net_interval:.6f}",
        "r_realized": f"{realized_return:.6f}",
        "roi_daily": f"{roi_daily_pct:.6f}",
        "pnl_daily": f"{pnl_daily:.6f}",
        "score": f"{working_pool['score']:.6f}",
        "capital_before": f"{capital_before:.6f}",
        "capital_after": f"{capital_after:.6f}",
        "treasury_delta": f"{treasury_delta:.6f}",
        "status": status_combined,
    }
    append_log(row, str(LOG_FILE))

    payload = {
        "pool": working_pool["name"],
        "chain": working_pool["chain"],
        "apy": working_pool["apy"],
        "r_day": working_pool["r_day"],
        "r_net_daily": r_net_daily,
        "r_net_interval": r_net_interval,
        "r_realized": realized_return,
        "capital_before": capital_before,
        "capital_after": capital_after,
        "treasury_delta": treasury_delta,
        "roi_daily": roi_daily_pct,
        "pnl_daily": pnl_daily,
        "score": working_pool["score"],
        "status": status_combined,
        "status_head": status_head,
        "status_tags": status_notes,
        "metadata": metadata_bits,
        "pool_changed": rotated_effective,
        "pool_requested_change": rotated,
        "portfolio_status": portfolio_status,
        "score_delta": working_pool["score"] - previous_score,
        "score_previous": previous_score,
        "schedule": config.schedule_utc,
        "interval_desc": interval_desc,
    }
    msg = build_telegram_message(payload)
    print(msg)
    send_telegram(msg, config)

    for note in extra_notifications:
        print(note)
        send_telegram(note, config)


if __name__ == "__main__":
    main()
