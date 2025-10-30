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

import argparse
import csv
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

try:  # Optional dependency – allows tests to import without network libs
    import requests
except ModuleNotFoundError:  # pragma: no cover - import guard branch
    requests = None  # type: ignore[assignment]

try:  # Optional dependency for wallet inspection
    from web3 import Web3
except ModuleNotFoundError:  # pragma: no cover - import guard branch
    Web3 = None  # type: ignore[assignment]

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs
    def load_dotenv(*_args, **_kwargs):  # type: ignore[override]
        return False

from data_sources import fetch_pools_scoped
from executor import move_capital_smart, settle_day
from execution_summary import create_execution_summary
from kill_switch import get_kill_switch
from logger import append_log, build_telegram_message, timestamp_now
from multi_strategy import (
    execute_multi_strategy,
    print_allocation_summary,
    MultiStrategyConfig,
)
from onchain import (
    push_strategy_update,
    update_active_pool,
    resume_vault,
    get_available_capital_eth,
    get_signer_context,
)
from run_lock import acquire_run_lock, RunLockError
from scoring import daily_cost, daily_rate, normalized_score, should_switch
from treasury import dispatch_treasury_payout

BASE_DIR = Path(__file__).resolve().parent
CAPITAL_FILE = BASE_DIR / "capital.txt"
TREASURY_FILE = BASE_DIR / "treasury.txt"
STATE_FILE = BASE_DIR / "state.json"
LOG_FILE = BASE_DIR / "log.csv"


DEFAULT_FX_EUR_PER_ETH = 3000.0
DEFAULT_TREASURY_MIN_EUR = 0.5

def _parse_env_set(name: str) -> set[str]:
    raw = os.getenv(name, "")
    items: set[str] = set()
    if not raw:
        return items
    for part in raw.split(","):
        entry = part.strip()
        if entry:
            items.add(entry.lower())
    return items


POOL_ALLOWLIST = _parse_env_set("POOL_ALLOWLIST")
POOL_DENYLIST = _parse_env_set("POOL_DENYLIST")

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

ERC20_BALANCE_DECIMALS_ABI = json.loads(
    """
[
  {
    "constant": true,
    "inputs": [{"name": "account", "type": "address"}],
    "name": "balanceOf",
    "outputs": [{"name": "", "type": "uint256"}],
    "payable": false,
    "stateMutability": "view",
    "type": "function"
  },
  {
    "constant": true,
    "inputs": [],
    "name": "decimals",
    "outputs": [{"name": "", "type": "uint8"}],
    "payable": false,
    "stateMutability": "view",
    "type": "function"
  }
]
"""
)


def _token_balance_threshold() -> float:
    raw = os.getenv("POOL_TOKEN_MIN_BALANCE", "1e-6")
    try:
        return float(raw)
    except ValueError:
        return 1e-6


def _extract_token_field(value: object, field_name: str) -> Optional[Tuple[str, str]]:
    if value is None:
        return None

    label = field_name
    env_name = None
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_name = value[2:-1]
        resolved = os.getenv(env_name, "")
        if env_name:
            label = env_name
    else:
        resolved = value

    if not isinstance(resolved, str):
        return None

    resolved = resolved.strip()
    if not resolved or not resolved.startswith("0x"):
        return None

    try:
        checksum = Web3.to_checksum_address(resolved) if Web3 is not None else resolved
    except Exception:
        checksum = resolved

    addr_lower = checksum.lower()

    if env_name is None and label == field_name:
        for name, env_val in os.environ.items():
            if isinstance(env_val, str) and env_val.lower() == addr_lower:
                label = name
                break

    return addr_lower, label


def _adapter_required_tokens(adapter_cfg: Optional[Dict[str, object]]) -> List[Tuple[str, str]]:
    if not adapter_cfg:
        return []
    adapter_type = str(adapter_cfg.get("type") or "").lower()
    fields = REQUIRED_TOKEN_FIELDS.get(adapter_type, ())
    tokens: List[Tuple[str, str]] = []
    for field in fields:
        spec = _extract_token_field(adapter_cfg.get(field), field)
        if spec:
            tokens.append(spec)
    return tokens


def _gather_required_token_labels(config: StrategyConfig) -> Dict[str, str]:
    labels: Dict[str, str] = {}
    for adapter_cfg in config.adapters.values():
        for addr, label in _adapter_required_tokens(adapter_cfg):
            labels.setdefault(addr, label)
    return labels


def _get_adapter_config(config: StrategyConfig, pool_id: str) -> Optional[Dict[str, object]]:
    if pool_id in config.adapters:
        return config.adapters[pool_id]
    key_with_prefix = pool_id if pool_id.startswith("pool:") else f"pool:{pool_id}"
    if key_with_prefix in config.adapters:
        return config.adapters[key_with_prefix]
    key_without_prefix = pool_id[5:] if pool_id.startswith("pool:") else pool_id
    if key_without_prefix in config.adapters:
        return config.adapters[key_without_prefix]
    return None


def collect_wallet_assets(
    config: StrategyConfig,
    w3,
    account_address: Optional[str],
) -> Tuple[Dict[str, float], Dict[str, str]]:
    token_labels = dict(_gather_required_token_labels(config))
    token_labels["native"] = "ETH"
    balances: Dict[str, float] = {key: 0.0 for key in token_labels}

    if w3 is None or Web3 is None or account_address is None:
        return balances, token_labels

    try:
        checksum_account = Web3.to_checksum_address(account_address)
    except Exception:
        checksum_account = account_address

    try:
        native_balance = w3.eth.get_balance(checksum_account)
        balances["native"] = float(Web3.from_wei(native_balance, "ether"))
    except Exception:
        pass

    decimals_cache: Dict[str, int] = {}
    for addr, label in token_labels.items():
        if addr == "native":
            continue
        try:
            checksum_token = Web3.to_checksum_address(addr)
        except Exception:
            checksum_token = addr
        try:
            contract = w3.eth.contract(address=checksum_token, abi=ERC20_BALANCE_DECIMALS_ABI)
            if addr not in decimals_cache:
                decimals_cache[addr] = contract.functions.decimals().call()
            decimals = decimals_cache[addr]
            raw_balance = contract.functions.balanceOf(checksum_account).call()
            balances[addr] = float(raw_balance) / (10 ** decimals)
        except Exception:
            balances.setdefault(addr, 0.0)
            continue

    return balances, token_labels


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
    treasury_start_day: float = 0.0
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
            treasury_start_day=float(raw.get("treasury_start_day", 0.0)),
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
            "treasury_start_day": self.treasury_start_day,
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


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def effective_reinvest_ratio(
    profit_eth: float,
    base_reinvest_ratio: float,
    *,
    fx_rate: float,
    min_payout_eur: float,
) -> float:
    """Return the reinvest ratio after applying the treasury payout threshold."""

    if profit_eth <= 0:
        return 1.0

    base = max(0.0, min(1.0, base_reinvest_ratio))
    treasury_ratio = 1.0 - base
    if treasury_ratio <= 0:
        return 1.0

    fx = max(fx_rate, 0.0)
    threshold = max(min_payout_eur, 0.0)

    treasury_share_eur = profit_eth * treasury_ratio * fx
    if treasury_share_eur >= threshold:
        return base
    return 1.0


def send_telegram(msg: str, config: StrategyConfig) -> None:
    tg_conf = config.telegram or {}
    if not tg_conf.get("enabled", False):
        return

    token = os.getenv(str(tg_conf.get("bot_token_env", "")) or "")
    chat_id = os.getenv(str(tg_conf.get("chat_id_env", "")) or "")
    if not token or not chat_id:
        print("[telegram] skipped: token/chat_id missing")
        return
    if requests is None:
        print("[telegram] skipped: requests not installed")
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


def select_best_pool(
    pools: List[Dict[str, float]],
    config: StrategyConfig,
    state: StrategyState,
    _w3,
    _capital_hint_eth: float,
    wallet_assets: Optional[Dict[str, float]] = None,
    token_labels: Optional[Dict[str, str]] = None,
) -> Tuple[Dict[str, object] | None, Dict[str, Dict[str, object]]]:
    def safe_float(value: object, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def pool_tvl(pool: Dict[str, object]) -> float:
        value = pool.get("tvl_usd")
        if value is None:
            value = pool.get("tvlUsd")
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    min_tvl = float(config.min_tvl_usd)
    candidates: List[Dict[str, object]] = []
    lookup: Dict[str, Dict[str, object]] = {}
    diagnostics: List[str] = []
    missing_assets_summary: Dict[str, List[str]] = {}
    eligible_ids: set[str] = set()

    balances = wallet_assets or {}
    labels = token_labels or {}
    token_threshold = _token_balance_threshold()

    for idx, pool in enumerate(pools):
        pool_id = str(pool.get("pool_id") or "").strip()
        if not pool_id:
            address = str(pool.get("address") or "").strip().lower()
            if address:
                pool_id = f"addr:{address}"
            else:
                chain = str(pool.get("chain") or "unknown").lower()
                project = str(pool.get("project") or "unknown").lower()
                pool_id = f"{chain}:{project}:{idx}"

        apy = safe_float(pool.get("apy"), 0.0)
        r_day = daily_rate(apy)
        cost_daily = daily_cost(pool)
        risk = max(0.0, min(1.0, safe_float(pool.get("risk_score"), 0.0)))
        score = normalized_score(pool)
        r_net = r_day - cost_daily
        tvl_value = pool_tvl(pool)

        candidate = dict(pool)
        candidate.update(
            {
                "pool_id": pool_id,
                "apy": apy,
                "r_day": r_day,
                "r_net": r_net,
                "score": score,
                "cost": cost_daily,
                "risk_score": risk,
                "tvl_usd": tvl_value,
            }
        )

        lookup[pool_id] = candidate

        pool_id_key = pool_id.lower()

        if POOL_ALLOWLIST and pool_id_key not in POOL_ALLOWLIST:
            diagnostics.append(f"{pool_id}:denied(allowlist)")
            continue
        if POOL_DENYLIST and pool_id_key in POOL_DENYLIST:
            diagnostics.append(f"{pool_id}:denied(denylist)")
            continue

        adapter_cfg = _get_adapter_config(config, pool_id)
        if not adapter_cfg:
            diagnostics.append(f"{pool_id}:no_adapter")
            continue

        requirements = _adapter_required_tokens(adapter_cfg)
        if requirements:
            missing_local: List[str] = []
            for addr, label in requirements:
                if addr == "native":
                    balance = balances.get("native", 0.0)
                    label_text = labels.get("native", "ETH")
                else:
                    balance = balances.get(addr, 0.0)
                    label_text = labels.get(addr, label)
                if balance <= token_threshold:
                    missing_local.append(label_text)
            if missing_local:
                missing_assets_summary[pool_id] = missing_local
                diagnostics.append(f"{pool_id}:missing:{'+'.join(missing_local)}")
                continue

        if tvl_value >= min_tvl:
            candidates.append(candidate)
            eligible_ids.add(pool_id)
        else:
            diagnostics.append(f"{pool_id or '?'}@{pool.get('chain', '?')}:tvl<{min_tvl:.0f}")

    if not candidates:
        if diagnostics:
            lookup["__diagnostics__"] = diagnostics
        if missing_assets_summary:
            lookup["__missing_assets__"] = missing_assets_summary
        return None, lookup

    ranking = sorted(candidates, key=lambda item: item["score"], reverse=True)
    best = ranking[0]

    current = lookup.get(state.pool_id) if state.pool_id else None
    if current:
        current_id = str(current.get("pool_id") or "").lower()
        if POOL_ALLOWLIST and current_id not in POOL_ALLOWLIST:
            diagnostics.append(f"{current.get('pool_id')}:drop(allowlist)")
            current = None
        elif POOL_DENYLIST and current_id in POOL_DENYLIST:
            diagnostics.append(f"{current.get('pool_id')}:drop(denylist)")
            current = None
        elif current.get("pool_id") not in eligible_ids:
            diagnostics.append(f"{current.get('pool_id')}:drop(ineligible)")
            current = None

    if missing_assets_summary:
        lookup["__missing_assets__"] = missing_assets_summary
    min_delta = float(config.delta_switch)

    if should_switch(best, current, min_delta=min_delta, last_switch_ts=state.last_switch_ts):
        return best, lookup

    return current or best, lookup

def push_onchain(selected: Dict[str, object], capital_token: float) -> Optional[str]:
    pool_name = selected["name"]
    apy_decimal = float(selected["apy"])
    # convert to percent
    apy_percent = apy_decimal * 100.0
    return push_strategy_update(pool_name, apy_percent, capital_token)


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Esegue la strategia Wave Rotation o mostra lo stato attuale.",
    )
    parser.add_argument(
        "--config",
        dest="config",
        default=str(BASE_DIR / "config.json"),
        help="Percorso del file di configurazione JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--print-status",
        action="store_true",
        help="Mostra un riepilogo dello stato corrente e termina",
    )
    return parser.parse_args(argv)


def _load_last_log_entry(log_path: Path) -> Optional[Dict[str, str]]:
    if not log_path.exists():
        return None
    try:
        with log_path.open(newline="") as fh:
            reader = csv.DictReader(fh)
            last_row: Optional[Dict[str, str]] = None
            for row in reader:
                last_row = row
            return last_row
    except Exception:
        return None


def print_strategy_status(
    config: Optional[StrategyConfig],
    state: StrategyState,
    *,
    config_path: Optional[Path] = None,
    config_error: Optional[str] = None,
) -> None:
    print("📊 Wave Rotation – stato corrente")

    if config_path is not None:
        if config_error:
            print(f"• Config: {config_path} (⚠️ {config_error})")
        else:
            print(f"• Config: {config_path}")

    if config is not None:
        print(
            "• Finestra schedulata: "
            f"{config.schedule_utc} UTC | Δ switch {config.delta_switch:.2%}"
        )
        chains = ", ".join(config.chains) if config.chains else "n/d"
        print(f"• Catene abilitate: {chains}")

    capital = load_decimal_file(CAPITAL_FILE, 0.0)
    treasury = load_decimal_file(TREASURY_FILE, 0.0)

    pool_name = state.pool_name or "n/d"
    chain = state.chain or "n/d"
    score = float(state.score if state.score is not None else 0.0)
    updated = state.updated_at or "n/d"

    print(f"• Pool attivo: {pool_name} ({chain}) | score {score:.6f}")
    print(f"• Ultimo aggiornamento: {updated}")
    pause_state = "attiva" if state.paused else "disattiva"
    print(
        "• Pausa automatica: "
        f"{pause_state} | streak crisi {state.crisis_streak}"
    )
    if state.last_crisis_at:
        print(f"  └─ Ultima crisi: {state.last_crisis_at}")
    if state.last_portfolio_move:
        print(f"  └─ Ultimo movimento portafoglio: {state.last_portfolio_move}")

    print(f"• Capitale corrente: {capital:.6f}")
    print(f"• Treasury cumulata: {treasury:.6f}")

    last_entry = _load_last_log_entry(LOG_FILE)
    if last_entry:
        date = last_entry.get("date", "?")
        status = last_entry.get("status", "?")
        capital_after = last_entry.get("capital_after")
        treasury_total = last_entry.get("treasury_total")
        extra_bits = []
        if capital_after:
            extra_bits.append(f"cap {capital_after}")
        if treasury_total:
            extra_bits.append(f"treasury {treasury_total}")
        tail = f" ({', '.join(extra_bits)})" if extra_bits else ""
        print(f"• Ultimo log: {date} – {status}{tail}")
    else:
        print("• Nessun log disponibile")


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = _parse_args(argv)

    load_dotenv()

    # Check kill-switch before proceeding
    kill_switch = get_kill_switch()
    try:
        kill_switch.check()
    except RuntimeError as exc:
        print(f"❌ {exc}")
        return

    # Acquire run-lock to prevent concurrent executions
    try:
        with acquire_run_lock():
            _run_strategy(args, kill_switch)
    except RunLockError as exc:
        print(f"⚠️ {exc}")
        return


def _run_strategy(args: argparse.Namespace, kill_switch) -> None:
    """Internal strategy execution (called within run-lock context)."""

    config_path = Path(args.config).expanduser()
    config: Optional[StrategyConfig] = None
    config_error: Optional[str] = None

    try:
        config = StrategyConfig.load(config_path)
    except FileNotFoundError:
        config_error = "file non trovato"
    except json.JSONDecodeError as exc:
        config_error = f"JSON non valido ({exc})"

    state = StrategyState.load(STATE_FILE)

    if args.print_status:
        print_strategy_status(
            config,
            state,
            config_path=config_path,
            config_error=config_error,
        )
        return

    if config is None:
        if config_error:
            raise SystemExit(
                f"Impossibile caricare la config {config_path}: {config_error}"
            )
        raise SystemExit(
            f"Impossibile caricare la config {config_path} (motivo sconosciuto)"
        )
    interval_seconds_env = os.getenv("WAVE_LOOP_INTERVAL_SECONDS")
    try:
        interval_seconds = int(interval_seconds_env) if interval_seconds_env else 300
    except ValueError:
        interval_seconds = 300
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
    w3 = None
    account = None
    if signer_ctx:
        _, w3, account = signer_ctx

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

    reserve_eth = float(os.getenv("GAS_RESERVE_ETH", "0.004"))
    available_onchain = get_available_capital_eth(reserve_eth)
    wallet_balances: Dict[str, float] = {}
    wallet_labels: Dict[str, str] = {}
    account_address = account.address if account is not None else None
    wallet_balances, wallet_labels = collect_wallet_assets(
        config,
        w3,
        account_address,
    )

    capital_file_exists = CAPITAL_FILE.exists()
    capital_hint_eth = load_decimal_file(CAPITAL_FILE, 100.0)
    if not capital_file_exists and available_onchain is not None:
        capital_hint_eth = available_onchain
        store_decimal_file(CAPITAL_FILE, capital_hint_eth)

    # Check if multi-strategy mode is enabled
    multi_config = MultiStrategyConfig.load()
    if multi_config.enabled:
        print("🎯 Multi-Strategy Optimizer ENABLED")
        
        dry_run_enabled = os.getenv("PORTFOLIO_DRY_RUN", "false").strip().lower() in {
            "1", "true", "yes", "on",
        }
        
        # Prepare config dict with adapters
        config_dict_full = {
            "chains": config.chains,
            "sources": config.sources,
            "adapters": config.adapters,
            "search_scope": os.getenv("SEARCH_SCOPE", config.selection.get("search_scope", "GLOBAL")),
        }
        
        # Execute multi-strategy
        allocations, execution_results = execute_multi_strategy(
            config_dict_full,
            wallet_balances,
            wallet_labels,
            w3,
            account,
            dry_run=dry_run_enabled,
        )
        
        # Print summary
        print_allocation_summary(allocations, execution_results)
        
        # Send telegram notification
        if allocations:
            allocation_summary = "\n".join([
                f"• {a.asset_label} → {a.pool_name} (${a.allocation_usd:.2f})"
                for a in allocations
            ])
            total_usd = sum(a.allocation_usd for a in allocations)
            msg = (
                "🎯 Multi-Strategy Allocation Complete\n\n"
                f"{allocation_summary}\n\n"
                f"💰 Total: ${total_usd:.2f}\n"
                f"🔄 Mode: {'DRY RUN' if dry_run_enabled else 'LIVE'}"
            )
        else:
            msg = "⚠️ Multi-Strategy: No viable allocations found"
        
        print(msg)
        send_telegram(msg, config)
        return
    
    # Standard Wave Rotation mode continues below
    selected, candidate_map = select_best_pool(
        pools,
        config,
        state,
        w3,
        capital_hint_eth,
        wallet_balances,
        wallet_labels,
    )
    if not selected:
        diagnostics = candidate_map.get("__diagnostics__") if candidate_map else None
        detail = ""
        if diagnostics:
            detail = "\n🔍 Dettagli: " + "; ".join(diagnostics)
        msg = "⚠️ Nessun pool supera i vincoli minimi (TVL, dati)." + detail
        print(msg)
        send_telegram(msg, config)
        return
    missing_assets_notes = candidate_map.get("__missing_assets__") if candidate_map else None
    if missing_assets_notes:
        parts = []
        for pid, items in missing_assets_notes.items():
            parts.append(f"{pid}: {', '.join(sorted(set(items)))}")
        if parts:
            print("ℹ️ Pool non allocabili per mancanza asset:", "; ".join(parts))

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

    gas_status_note: Optional[str] = None
    if available_onchain is not None:
        if available_onchain <= 0:
            gas_status_note = "gas:insufficient"
        elif available_onchain < reserve_eth:
            gas_status_note = "gas:low"

    capital_before = capital_hint_eth
    treasury_total = load_decimal_file(TREASURY_FILE, 0.0)

    current_day = datetime.utcnow().strftime("%Y-%m-%d")
    if (
        state.day_utc != current_day
        or state.capital_start_day <= 0
        or state.treasury_start_day < 0
    ):
        state.day_utc = current_day
        state.capital_start_day = capital_before if capital_before > 0 else 1.0
        state.treasury_start_day = treasury_total

    capital_start_day = state.capital_start_day if state.capital_start_day > 0 else 1.0
    treasury_start_day = state.treasury_start_day if state.treasury_start_day >= 0 else 0.0

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
    interval_multiplier = 1.0 + r_net_interval
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

    realized_interval_multiplier = 1.0
    realized_interval_profit = 0.0
    capital_gross_after = capital_before

    fx_rate = _float_env("FX_EUR_PER_ETH", DEFAULT_FX_EUR_PER_ETH)
    treasury_min_eur = _float_env("TREASURY_MIN_EUR", DEFAULT_TREASURY_MIN_EUR)
    reinvest_ratio_effective = 1.0

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
        profit_preview = capital_before * r_net_interval
        reinvest_ratio_effective = effective_reinvest_ratio(
            profit_preview,
            config.reinvest_ratio,
            fx_rate=fx_rate,
            min_payout_eur=treasury_min_eur,
        )
        profit, capital_after, treasury_delta_planned = settle_day(
            capital_before, r_net_interval, reinvest_ratio_effective
        )
        realized_interval_multiplier = interval_multiplier
        realized_interval_profit = profit
        capital_gross_after = capital_before + profit
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

    realized_return = (
        realized_interval_profit / capital_before if capital_before > 0 else 0.0
    )

    capital_basis_start = capital_start_day
    capital_basis_end = capital_gross_after
    pnl_capital = capital_basis_end - capital_basis_start
    roi_capital_pct = (
        (pnl_capital / capital_basis_start) * 100 if capital_basis_start else 0.0
    )

    total_assets_after = capital_after + treasury_total
    total_assets_start = capital_start_day + treasury_start_day
    pnl_total = total_assets_after - total_assets_start
    roi_total_pct = (
        (pnl_total / total_assets_start) * 100 if total_assets_start else 0.0
    )

    row = {
        "date": timestamp_now(),
        "pool": working_pool["name"],
        "chain": working_pool["chain"],
        "apy": f"{working_pool['apy']:.6f}",
        "r_day": f"{working_pool['r_day']:.6f}",
        "r_net_daily": f"{r_net_daily:.6f}",
        "r_net_interval": f"{r_net_interval:.6f}",
        "r_realized": f"{realized_return:.6f}",
        "interval_multiplier": f"{realized_interval_multiplier:.6f}",
        "interval_profit": f"{realized_interval_profit:.6f}",
        "reinvest_ratio": f"{reinvest_ratio_effective:.6f}",
        "capital_gross_after": f"{capital_gross_after:.6f}",
        "roi_daily": f"{roi_capital_pct:.6f}",
        "roi_total": f"{roi_total_pct:.6f}",
        "pnl_daily": f"{pnl_capital:.6f}",
        "pnl_total": f"{pnl_total:.6f}",
        "score": f"{working_pool['score']:.6f}",
        "capital_before": f"{capital_before:.6f}",
        "capital_after": f"{capital_after:.6f}",
        "treasury_delta": f"{treasury_delta:.6f}",
        "treasury_total": f"{treasury_total:.6f}",
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
        "interval_multiplier": realized_interval_multiplier,
        "interval_profit": realized_interval_profit,
        "capital_gross_after": capital_gross_after,
        "capital_before": capital_before,
        "capital_after": capital_after,
        "treasury_delta": treasury_delta,
        "roi_daily": roi_capital_pct,
        "roi_capital": roi_capital_pct,
        "roi_total": roi_total_pct,
        "pnl_daily": pnl_capital,
        "pnl_capital": pnl_capital,
        "pnl_total": pnl_total,
        "treasury_total": treasury_total,
        "reinvest_ratio": reinvest_ratio_effective,
        "reinvest_ratio_planned": config.reinvest_ratio,
        "treasury_threshold_eur": treasury_min_eur,
        "fx_eur_per_eth": fx_rate,
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
    
    # Create and print execution summary
    summary = create_execution_summary(
        dry_run=dry_run_enabled,
        multi_strategy=False,
    )
    summary.active_pool = working_pool.get("pool_id")
    summary.adapter_type = working_pool.get("adapter_source") or "unknown"
    summary.pool_chain = working_pool.get("chain")
    summary.amount_in = capital_before
    summary.amount_out = capital_after
    summary.realized_pnl = realized_interval_profit
    summary.treasury_move = treasury_delta > 0
    summary.treasury_amount = treasury_delta if treasury_delta > 0 else None
    
    if crisis_flag:
        summary.add_warning("Stop-loss triggered")
    if autopause_triggered:
        summary.add_warning("Auto-pause activated")
    if portfolio_status.startswith("SKIP"):
        summary.treasury_reason = portfolio_status
        summary.add_note(f"Portfolio movement skipped: {portfolio_status}")
    
    # Record success in kill-switch
    kill_switch.record_success()
    
    print("\n" + summary.format_text())


if __name__ == "__main__":
    main()
