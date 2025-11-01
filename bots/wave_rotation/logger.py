#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Logging helpers for Attuario Wave Rotation."""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
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
    "interval_multiplier",
    "interval_profit",
    "reinvest_ratio",
    "capital_gross_after",
    "roi_daily",
    "roi_total",
    "pnl_daily",
    "pnl_total",
    "score",
    "capital_before",
    "capital_after",
    "treasury_delta",
    "treasury_total",
    "status",
)


def append_log(row: Dict[str, str], log_path: str) -> None:
    exists = os.path.exists(log_path)
    needs_upgrade = False
    existing_rows: list[Dict[str, str]] = []
    header_missing = True

    if exists:
        with open(log_path, "r", newline="") as fh:
            reader = csv.DictReader(fh)
            fieldnames = reader.fieldnames
            if fieldnames:
                header_missing = False
                if list(fieldnames) != list(COLUMNS):
                    needs_upgrade = True
                    existing_rows = [dict(row) for row in reader]
            else:
                header_missing = True

    mode = "w" if needs_upgrade else "a"
    with open(log_path, mode, newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)

        if needs_upgrade:
            writer.writeheader()
            for old_row in existing_rows:
                normalized = {key: old_row.get(key, "") for key in COLUMNS}
                writer.writerow(normalized)
        elif not exists or header_missing:
            writer.writeheader()

        writer.writerow({key: row.get(key, "") for key in COLUMNS})


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
    roi_capital = float(
        payload.get("roi_capital", payload.get("roi_daily", 0.0)) or 0.0
    )
    pnl_capital = float(
        payload.get("pnl_capital", payload.get("pnl_daily", 0.0)) or 0.0
    )
    roi_total_val = payload.get("roi_total")
    pnl_total_val = payload.get("pnl_total")
    interval_multiplier = float(payload.get("interval_multiplier", 1.0))
    interval_profit = float(payload.get("interval_profit", 0.0))
    capital_gross_after = float(payload.get("capital_gross_after", capital_after))
    reinvest_ratio = float(payload.get("reinvest_ratio", 1.0))
    reinvest_ratio_planned = float(
        payload.get("reinvest_ratio_planned", reinvest_ratio) or reinvest_ratio
    )
    score = float(payload.get("score", 0.0))
    score_previous = float(payload.get("score_previous", 0.0))
    score_delta = float(payload.get("score_delta", 0.0))

    lines = [header]
    lines.append(
        "📈 Previsto: "
        f"APY annuo {apy:.2%} | r₍daily₎ {r_net_daily:.4%} (comp.) | r₍interval₎ {r_net_interval:.4%}"
    )
    lines.append(
        f"📊 Realizzato: r₍interval₎ {r_realized:.4%} | moltiplicatore ×{interval_multiplier:.6f}"
    )
    lines.append(
        f"💵 Rendimento ciclo: ×{interval_multiplier:.6f} | Profitto {interval_profit:+.6f} ETH"
    )

    reinvest_pct = reinvest_ratio * 100.0
    if reinvest_ratio >= 0.999:
        if reinvest_ratio_planned < 0.999:
            capital_line = (
                "💰 Capitale reinvestito: "
                f"{capital_before:.6f} ETH → {capital_after:.6f} ETH "
                "(soglia treasury non raggiunta)"
            )
        else:
            capital_line = (
                f"💰 Capitale reinvestito: {capital_before:.6f} ETH → {capital_after:.6f} ETH"
            )
    else:
        capital_line = (
            "💰 Capitale reinvestito ("
            f"{reinvest_pct:.1f}% profitto): {capital_before:.6f} ETH → {capital_after:.6f} ETH"
        )
    lines.append(capital_line)
    lines.append(
        f"💵 Valore a riscatto: {capital_before:.6f} ETH × {interval_multiplier:.6f} = {capital_gross_after:.6f} ETH"
    )
    treasury_label = "+" if treasury_delta >= 0 else ""
    treasury_total = float(payload.get("treasury_total", 0.0))
    lines.append(
        f"🏦 Treasury {treasury_label}{treasury_delta:.6f} ETH (totale {treasury_total:.6f} ETH)"
    )
    lines.append(
        f"📆 ROI capitale (giorno): {roi_capital:.3f}% | PnL capitale: {pnl_capital:+.6f} ETH"
    )
    if roi_total_val is not None and pnl_total_val is not None:
        roi_total = float(roi_total_val)
        pnl_total = float(pnl_total_val)
        if (
            abs(roi_total - roi_capital) > 1e-9
            or abs(pnl_total - pnl_capital) > 1e-9
        ):
            lines.append(
                "📊 ROI patrimonio (con treasury): "
                f"{roi_total:.3f}% | PnL totale: {pnl_total:+.6f} ETH"
            )

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
    """UTC timestamp helper using timezone-aware datetime."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
