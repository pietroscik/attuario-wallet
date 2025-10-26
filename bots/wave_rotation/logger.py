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


def build_telegram_message(payload: Dict[str, float | str]) -> str:
    status = payload.get("status", "executed")
    interval = payload.get("interval_desc", "24h")
    onchain_status = status
    lines = [
        f"🏁 Pool del giorno: {payload['pool']} ({payload['chain']})",
        "📈 Previsto: "
        f"APY {payload['apy']:.2%} | r₍daily₎ {payload['r_net_daily']:.4%} | r₍interval₎ {payload['r_net_interval']:.4%}",
        f"📊 Realizzato: r₍interval₎ {payload['r_realized']:.4%}",
        f"💰 Capitale: {payload['capital_before']:.6f} ETH → {payload['capital_after']:.6f} ETH",
        f"🏦 Treasury +{payload['treasury_delta']:.6f} ETH",
        f"📆 ROI giornaliero: {payload['roi_daily']:.3f}% | PnL: {payload['pnl_daily']:.6f} ETH",
        f"📊 Score: {payload['score']:.6f} | Stato: {status}",
        f"⏱️ Next run: {interval}",
        f"🔗 Stato on-chain: {onchain_status}",
    ]
    return "\n".join(lines)


def timestamp_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
