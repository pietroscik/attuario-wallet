#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Logging helpers for Attuario Wave Rotation."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Dict, Iterable

COLUMNS: Iterable[str] = (
    "date",
    "pool",
    "chain",
    "apy",
    "r_day",
    "r_net_daily",
    "r_net_interval",
    "r_realized",
    "roi_daily",
    "pnl_daily",
    "score",
    "capital_before",
    "capital_after",
    "treasury_delta",
    "status",
)


def append_log(row: Dict[str, str], log_path: str) -> None:
    exists = os.path.exists(log_path)
    with open(log_path, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def _format_status_block(status_head: str, status_tags: Iterable[str]) -> str:
    if not status_tags:
        return f"🧾 Stato: {status_head}"
    bullet_lines = "\n".join(f"   • {tag}" for tag in status_tags)
    return f"🧾 Stato: {status_head}\n{bullet_lines}"


def build_telegram_message(payload: Dict[str, float | str]) -> str:
    status_head = str(payload.get("status_head") or payload.get("status") or "executed")
    interval = payload.get("interval_desc", "24h")
    pool = payload.get("pool", "?")
    chain = payload.get("chain", "?")

    pool_changed = bool(payload.get("pool_changed"))
    requested_change = bool(payload.get("pool_requested_change"))

    if status_head.startswith("stopped"):
        header = f"🛑 Stop-loss su {pool} ({chain})"
    elif status_head.startswith("paused"):
        header = f"⏸️ Valutazione in pausa: {pool} ({chain})"
    elif pool_changed:
        header = f"🔄 Nuovo pool: {pool} ({chain})"
    elif requested_change and not pool_changed:
        header = f"⚖️ Pool invariato dopo verifica: {pool} ({chain})"
    else:
        header = f"♻️ Pool invariato: {pool} ({chain})"

    apy = float(payload.get("apy", 0.0))
    r_net_daily = float(payload.get("r_net_daily", 0.0))
    r_net_interval = float(payload.get("r_net_interval", 0.0))
    r_realized = float(payload.get("r_realized", 0.0))
    capital_before = float(payload.get("capital_before", 0.0))
    capital_after = float(payload.get("capital_after", 0.0))
    treasury_delta = float(payload.get("treasury_delta", 0.0))
    roi_daily = float(payload.get("roi_daily", 0.0))
    pnl_daily = float(payload.get("pnl_daily", 0.0))
    score = float(payload.get("score", 0.0))
    score_previous = float(payload.get("score_previous", 0.0))
    score_delta = float(payload.get("score_delta", 0.0))

    lines = [header]
    lines.append(
        "📈 Previsto: "
        f"APY {apy:.2%} | r₍daily₎ {r_net_daily:.4%} | r₍interval₎ {r_net_interval:.4%}"
    )
    lines.append(f"📊 Realizzato: r₍interval₎ {r_realized:.4%}")

    lines.append(
        f"💰 Capitale: {capital_before:.6f} ETH → {capital_after:.6f} ETH"
    )
    treasury_label = "+" if treasury_delta >= 0 else ""
    lines.append(f"🏦 Treasury {treasury_label}{treasury_delta:.6f} ETH")
    lines.append(f"📆 ROI giornaliero: {roi_daily:.3f}% | PnL: {pnl_daily:.6f} ETH")

    delta_sign = "+" if score_delta >= 0 else ""
    lines.append(
        f"📊 Score: {score:.6f} ({delta_sign}{score_delta:.6f} vs {score_previous:.6f})"
    )

    status_tags = list(payload.get("status_tags") or [])
    lines.append(_format_status_block(status_head, status_tags))

    portfolio_status = payload.get("portfolio_status")
    if portfolio_status:
        lines.append(f"📦 Portfolio: {portfolio_status}")

    metadata = list(payload.get("metadata") or [])
    if metadata:
        lines.append("🛠️ Meta: " + ", ".join(metadata))

    lines.append(f"⏱️ Prossimo controllo: {interval}")

    return "\n".join(lines)


def timestamp_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
