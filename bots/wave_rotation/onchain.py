#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""On-chain helpers for Attuario Adaptive Vault."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from pathlib import Path
from typing import Optional, Tuple

from eth_account import Account
from web3 import HTTPProvider, Web3
from web3.contract.contract import ContractFunction
from web3.middleware.proof_of_authority import ExtraDataToPOAMiddleware

# === Multi-RPC failover setup =============================================

if os.getenv("RPC_URLS"):
    RPCS = [url.strip() for url in os.getenv("RPC_URLS").split(",") if url.strip()]
else:
    primary = os.getenv("RPC_URL")
    fallbacks = [
        url.strip() for url in os.getenv("RPC_FALLBACKS", "").split(",") if url.strip()
    ]
    RPCS = [url for url in [primary] + fallbacks if url]

if not RPCS:
    raise RuntimeError(
        "RPC configuration missing: set RPC_URL or RPC_URLS/RPC_FALLBACKS"
    )

ALLOWED_CHAIN_IDS = {
    int(x)
    for x in os.getenv("ALLOWED_CHAIN_IDS", "8453,84532").split(",")
    if x.strip()
}
REQUIRE_BASE = os.getenv("REQUIRE_BASE", "false").strip().lower() == "true"
BASE_CHAIN_ID = 8453

RPC_TIMEOUT = float(os.getenv("RPC_TIMEOUT_S", "20"))
MAX_BLOCK_STALENESS_S = float(os.getenv("MAX_BLOCK_STALENESS_S", "90"))
RPC_MAX_RETRIES = int(os.getenv("RPC_MAX_RETRIES", "2"))

_current_index = 0
_current_rpc_url = None
_last_switch_reason = "-"
_w3: Web3 | None = None


def _make_w3(url: str) -> Web3:
    provider = HTTPProvider(url, request_kwargs={"timeout": RPC_TIMEOUT})
    w = Web3(provider)
    try:
        w.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    except ValueError:
        pass
    return w


def _connect(start_index: int = 0) -> None:
    global _w3, _current_index, _current_rpc_url
    errors = []
    total = len(RPCS)
    for step in range(total):
        idx = (start_index + step) % total
        url = RPCS[idx]
        try:
            candidate = _make_w3(url)
            if not candidate.is_connected():
                raise RuntimeError("not connected")
            chain_id = candidate.eth.chain_id
            if ALLOWED_CHAIN_IDS and chain_id not in ALLOWED_CHAIN_IDS:
                raise RuntimeError(f"chainId {chain_id} not allowed")
            if REQUIRE_BASE and chain_id != BASE_CHAIN_ID:
                raise RuntimeError(
                    f"REQUIRE_BASE enforced but chainId={chain_id}"
                )
            latest = candidate.eth.get_block("latest")
            if (time.time() - latest["timestamp"]) > MAX_BLOCK_STALENESS_S:
                raise RuntimeError("node stale (latest block too old)")
            _w3 = candidate
            _current_index = idx
            _current_rpc_url = url
            return
        except Exception as exc:  # pragma: no cover - failover path
            errors.append(f"{url}: {exc}")
            continue
    raise RuntimeError("RPC_FAILOVER_EXHAUSTED:\n  " + "\n  ".join(errors))


def switch_rpc(reason: str = "manual") -> str:
    global _last_switch_reason
    _last_switch_reason = reason
    _connect(_current_index + 1)
    return _current_rpc_url  # type: ignore


def rpc_info() -> dict:
    return {
        "url": _current_rpc_url,
        "index": _current_index,
        "allowed": sorted(ALLOWED_CHAIN_IDS),
        "last_switch_reason": _last_switch_reason,
    }


def _rpc_try(fn, *args, **kwargs):
    last_exc = None
    for attempt in range(RPC_MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - retry path
            last_exc = exc
            if attempt < RPC_MAX_RETRIES:
                switch_rpc(f"exc:{type(exc).__name__}")
                continue
            raise last_exc


_connect(0)
w3 = _w3  # type: ignore
cid = w3.eth.chain_id  # type: ignore
current_rpc_url = _current_rpc_url


@dataclass
class OnchainConfig:
    rpc_url: str
    private_key: str
    vault_address: str
    abi_path: Path
    capital_scale: Decimal


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _load_config() -> Optional[OnchainConfig]:
    if not _env_bool("ONCHAIN_ENABLED", False):
        return None

    rpc_url = current_rpc_url or os.getenv("RPC_URL") or RPCS[0]
    private_key = os.getenv("PRIVATE_KEY")
    vault_address = os.getenv("VAULT_ADDRESS")

    repo_root = Path(__file__).resolve().parents[2]
    default_v2 = (
        repo_root
        / "contracts"
        / "artifacts"
        / "contracts"
        / "AttuarioVaultV2_Adaptive.sol"
        / "AttuarioVaultV2_Adaptive.json"
    )
    if default_v2.exists():
        default_abi = default_v2
    else:
        default_abi = (
            repo_root
            / "contracts"
            / "artifacts"
            / "contracts"
            / "AttuarioVault.sol"
            / "AttuarioVault.json"
        )
    abi_path = Path(os.getenv("VAULT_ABI_PATH", str(default_abi)))

    scale_raw = os.getenv("CAPITAL_SCALE", "1000000")
    try:
        capital_scale = Decimal(scale_raw)
    except InvalidOperation:
        print(f"[onchain] Valore CAPITAL_SCALE non valido: {scale_raw}")
        capital_scale = Decimal("1000000")

    missing = [
        name
        for name, value in (
            ("PRIVATE_KEY", private_key),
            ("VAULT_ADDRESS", vault_address),
        )
        if not value
    ]
    if missing:
        print(f"[onchain] Config mancante: {', '.join(missing)}")
        return None

    if not abi_path.exists():
        print(f"[onchain] ABI non trovata: {abi_path}")
        return None

    return OnchainConfig(
        rpc_url=rpc_url,
        private_key=private_key,
        vault_address=vault_address,
        abi_path=abi_path,
        capital_scale=capital_scale,
    )


def _apy_to_basis_points(apy_percent: float) -> int:
    try:
        apy = Decimal(str(apy_percent))
    except InvalidOperation:
        return 0
    value = apy * Decimal("100")
    return max(0, int(value.to_integral_value(rounding=ROUND_DOWN)))


def _capital_to_units(capital: float, scale: Decimal) -> int:
    try:
        cap = Decimal(str(capital))
    except InvalidOperation:
        cap = Decimal("0")
    quantized = cap * scale
    return max(0, int(quantized.to_integral_value(rounding=ROUND_DOWN)))


def _load_base_context() -> Optional[Tuple[OnchainConfig, Web3, Account]]:
    cfg = _load_config()
    if cfg is None:
        return None
    if w3 is None:
        raise RuntimeError("RPC connection unavailable")
    account = Account.from_key(cfg.private_key)
    return cfg, w3, account


def get_signer_context() -> Optional[Tuple[OnchainConfig, Web3, Account]]:
    """Public helper for modules that need direct web3/account access."""
    return _load_base_context()


def _prepare_contract():
    ctx = _load_base_context()
    if ctx is None:
        return None
    cfg, w3, account = ctx

    with cfg.abi_path.open(encoding="utf-8") as fh:
        artifact = json.load(fh)
    abi = artifact.get("abi")
    if not abi:
        print("[onchain] ABI non valida")
        return None

    checksum_address = Web3.to_checksum_address(cfg.vault_address)
    contract = w3.eth.contract(address=checksum_address, abi=abi)
    return cfg, w3, account, contract


def get_available_capital_eth(reserve_eth: float = 0.004) -> Optional[float]:
    cfg = _load_config()
    if cfg is None:
        return None

    if w3 is None:
        return None

    account = Account.from_key(cfg.private_key)
    try:
        balance_wei = _rpc_try(lambda: w3.eth.get_balance(account.address))
    except Exception as err:  # pragma: no cover - network failure path
        print(f"[onchain] Impossibile ottenere il saldo on-chain: {err}")
        return None

    balance_eth = float(Web3.from_wei(balance_wei, "ether"))
    available = balance_eth - reserve_eth
    return available if available > 0 else 0.0


def _send_contract_tx(w3: Web3, account, tx_fn: ContractFunction, label: str) -> Optional[str]:
    try:
        nonce = _rpc_try(lambda: w3.eth.get_transaction_count(account.address))
        gas_estimate = _rpc_try(lambda: tx_fn.estimate_gas({"from": account.address}))
    except Exception as err:
        print(f"[onchain] {label} stima gas fallita: {err}")
        return None

    tx = tx_fn.build_transaction(
        {
            "chainId": w3.eth.chain_id,
            "from": account.address,
            "nonce": nonce,
            "gas": int(gas_estimate * Decimal("1.2")),
            "gasPrice": _rpc_try(lambda: w3.eth.gas_price),
            "value": 0,
        }
    )

    try:
        signed = account.sign_transaction(tx)
        raw_tx = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction", None)
        if raw_tx is None:
            raise AttributeError("SignedTransaction missing raw bytes")
        tx_hash = _rpc_try(lambda: w3.eth.send_raw_transaction(raw_tx))
        print(f"[onchain] {label} inviato: {tx_hash.hex()}")
        return tx_hash.hex()
    except Exception as err:
        print(f"[onchain] Invio {label} fallito: {err}")
        return None


def execute_strategy(pool_name: str, apy_percent: float, capital_amount: float) -> Optional[str]:
    ctx = _prepare_contract()
    if ctx is None:
        return None
    cfg, w3, account, contract = ctx

    apy_bps = _apy_to_basis_points(apy_percent)
    capital_units = _capital_to_units(capital_amount, cfg.capital_scale)

    return _send_contract_tx(
        w3,
        account,
        contract.functions.executeStrategy(pool_name, apy_bps, capital_units),
        "executeStrategy",
    )


def update_active_pool(pool_name: str, crisis: bool) -> Optional[str]:
    ctx = _prepare_contract()
    if ctx is None:
        return None
    _, w3, account, contract = ctx
    return _send_contract_tx(
        w3,
        account,
        contract.functions.setActivePool(pool_name, crisis),
        "setActivePool",
    )


def pause_vault() -> Optional[str]:
    ctx = _prepare_contract()
    if ctx is None:
        return None
    _, w3, account, contract = ctx
    return _send_contract_tx(w3, account, contract.functions.pauseVault(), "pauseVault")


def resume_vault() -> Optional[str]:
    ctx = _prepare_contract()
    if ctx is None:
        return None
    _, w3, account, contract = ctx
    return _send_contract_tx(w3, account, contract.functions.resumeVault(), "resumeVault")


def emergency_withdraw(to: str) -> Optional[str]:
    ctx = _prepare_contract()
    if ctx is None:
        return None
    _, w3, account, contract = ctx
    return _send_contract_tx(w3, account, contract.functions.emergencyWithdraw(to), "emergencyWithdraw")


def sweep_erc20(token: str, to: str) -> Optional[str]:
    ctx = _prepare_contract()
    if ctx is None:
        return None
    _, w3, account, contract = ctx
    return _send_contract_tx(w3, account, contract.functions.sweepERC20(token, to), "sweepERC20")


# Retro-compatibilità con la vecchia funzione
def push_strategy_update(pool_name: str, apy_percent: float, capital_amount: float) -> Optional[str]:
    return execute_strategy(pool_name, apy_percent, capital_amount)
