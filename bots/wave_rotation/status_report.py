#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Valutazione operativa della strategia Wave Rotation.

Il report fornisce una fotografia immediata delle tre fasi principali:

* **Deploy** – stato dell'automazione (on-chain, portfolio, treasury) e dei
  file locali di capitale.
* **Investment** – ultimo ciclo eseguito, pool attivo, variazioni di capitale
  e ROI.
* **Corrections** – verifica delle pause automatiche, crisi in corso e tag di
  stato che richiedono attenzione.

Eseguire con:

```
python bots/wave_rotation/status_report.py
```

Passare ``--json`` per un output machine-friendly.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback per ambienti minimi
    def load_dotenv(*_args, **_kwargs):  # type: ignore[override]
        return False


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CAPITAL_FILE = BASE_DIR / "capital.txt"
TREASURY_FILE = BASE_DIR / "treasury.txt"
STATE_FILE = BASE_DIR / "state.json"
LOG_FILE = BASE_DIR / "log.csv"


SEVERITY_ICON = {
    "ok": "✅",
    "warn": "⚠️",
    "error": "❌",
    "info": "ℹ️",
}


@dataclass
class StatusItem:
    label: str
    value: str
    severity: str = "info"
    hint: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        return {k: v for k, v in payload.items() if v is not None}


def _bool_env(name: str) -> bool:
    raw = os.getenv(name, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _load_json(path: Path) -> Dict[str, object] | None:
    if not path.exists():
        return None
    try:
        with path.open() as fh:
            return json.load(fh)
    except json.JSONDecodeError:
        return None


def _read_last_log_row(path: Path) -> Dict[str, str] | None:
    if not path.exists():
        return None
    last_row: Dict[str, str] | None = None
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            last_row = row
    return last_row


def _parse_dt(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_float(row: Dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "0") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _read_decimal_file(path: Path) -> Optional[float]:
    if not path.exists():
        return None
    try:
        return float(path.read_text().strip())
    except ValueError:
        return None


def _format_age(ts: datetime | None) -> str:
    if ts is None:
        return "sconosciuto"
    now = datetime.now(timezone.utc)
    delta = now - ts
    hours = delta.total_seconds() / 3600
    if hours < 1:
        return f"{int(delta.total_seconds() // 60)} minuti fa"
    return f"{hours:.1f}h fa"


def _deploy_status(state: Dict[str, object] | None) -> List[StatusItem]:
    items: List[StatusItem] = []

    onchain_enabled = _bool_env("ONCHAIN_ENABLED")
    rpc_configured = bool(os.getenv("RPC_URLS") or os.getenv("RPC_URL"))
    pk_configured = bool(os.getenv("PRIVATE_KEY"))
    vault_configured = bool(os.getenv("VAULT_ADDRESS"))

    if onchain_enabled:
        missing: List[str] = []
        if not rpc_configured:
            missing.append("RPC_URL/RPC_URLS")
        if not pk_configured:
            missing.append("PRIVATE_KEY")
        if not vault_configured:
            missing.append("VAULT_ADDRESS")
        if missing:
            items.append(
                StatusItem(
                    "Esecuzione on-chain",
                    "Abilitata ma incompleta",
                    severity="error",
                    hint="Configura " + ", ".join(missing),
                )
            )
        else:
            items.append(
                StatusItem(
                    "Esecuzione on-chain",
                    "Abilitata",
                    severity="ok",
                    hint="RPC e credenziali disponibili",
                )
            )
    else:
        items.append(
            StatusItem(
                "Esecuzione on-chain",
                "Disattivata",
                severity="warn",
                hint="ONCHAIN_ENABLED=false: nessuna transazione verrà inviata",
            )
        )

    portfolio_enabled = _bool_env("PORTFOLIO_AUTOMATION_ENABLED")
    dry_run = _bool_env("PORTFOLIO_DRY_RUN")
    if portfolio_enabled:
        hint = "modalità dry-run attiva" if dry_run else None
        items.append(
            StatusItem(
                "Portfolio automation",
                "Abilitata",
                severity="ok",
                hint=hint,
            )
        )
    else:
        items.append(
            StatusItem(
                "Portfolio automation",
                "Disattivata",
                severity="warn",
                hint="PORTFOLIO_AUTOMATION_ENABLED=false",
            )
        )

    treasury_enabled = _bool_env("TREASURY_AUTOMATION_ENABLED")
    if treasury_enabled:
        treasury_address = os.getenv("TREASURY_ADDRESS")
        if not treasury_address:
            items.append(
                StatusItem(
                    "Tesoreria automatica",
                    "Abilitata ma incompleta",
                    severity="error",
                    hint="TREASURY_ADDRESS mancante",
                )
            )
        else:
            items.append(
                StatusItem(
                    "Tesoreria automatica",
                    "Abilitata",
                    severity="ok",
                    hint=f"Indirizzo treasury {treasury_address}",
                )
            )
    else:
        items.append(
            StatusItem(
                "Tesoreria automatica",
                "Disattivata",
                severity="warn",
                hint="TREASURY_AUTOMATION_ENABLED=false: payout manuale",
            )
        )

    capital_value = _read_decimal_file(CAPITAL_FILE)
    if capital_value is None:
        items.append(
            StatusItem(
                "File capitale",
                "Assente",
                severity="warn",
                hint=str(CAPITAL_FILE.name) + " non inizializzato",
            )
        )
    else:
        items.append(
            StatusItem(
                "File capitale",
                f"{capital_value:.6f} ETH",
                severity="ok",
            )
        )

    treasury_value = _read_decimal_file(TREASURY_FILE)
    if treasury_value is None:
        items.append(
            StatusItem(
                "File treasury",
                "Assente",
                severity="info",
                hint="Verrà popolato alla prima distribuzione",
            )
        )
    else:
        items.append(
            StatusItem(
                "File treasury",
                f"{treasury_value:.6f} ETH",
                severity="info",
            )
        )

    if state is not None:
        last_update = _parse_dt(str(state.get("updated_at")))
        items.append(
            StatusItem(
                "Ultimo aggiornamento stato",
                str(state.get("updated_at") or "-"),
                severity="info",
                hint=_format_age(last_update),
            )
        )

    return items


def _investment_status(
    state: Dict[str, object] | None, last_log: Dict[str, str] | None
) -> List[StatusItem]:
    items: List[StatusItem] = []

    if last_log is None:
        items.append(
            StatusItem(
                "Log esecuzioni",
                "Non disponibile",
                severity="error",
                hint=f"Esegui la strategia per generare {LOG_FILE.name}",
            )
        )
        return items

    last_ts = _parse_dt(last_log.get("date"))
    age_label = _format_age(last_ts)
    if last_ts is None:
        severity = "warn"
    else:
        hours = (datetime.now(timezone.utc) - last_ts).total_seconds() / 3600
        if hours > 48:
            severity = "error"
        elif hours > 24:
            severity = "warn"
        else:
            severity = "ok"

    items.append(
        StatusItem(
            "Ultima esecuzione",
            last_log.get("date", "-"),
            severity=severity,
            hint=age_label,
        )
    )

    pool_name = last_log.get("pool", "?")
    pool_chain = last_log.get("chain", "?")
    score = _parse_float(last_log, "score")
    items.append(
        StatusItem(
            "Pool attivo",
            f"{pool_name} ({pool_chain})",
            severity="info",
            hint=f"score {score:.6f}",
        )
    )

    capital_before = _parse_float(last_log, "capital_before")
    capital_after = _parse_float(last_log, "capital_after")
    delta_capital = capital_after - capital_before
    items.append(
        StatusItem(
            "Capitale",
            f"{capital_after:.6f} ETH",
            severity="info",
            hint=f"Δ {delta_capital:+.6f} ETH rispetto al ciclo precedente",
        )
    )

    roi_daily = _parse_float(last_log, "roi_daily")
    pnl_daily = _parse_float(last_log, "pnl_daily")
    roi_total = _parse_float(last_log, "roi_total")
    pnl_total = _parse_float(last_log, "pnl_total")
    hint_roi = f"PnL capitale {pnl_daily:.6f} ETH"
    if (
        abs(roi_total - roi_daily) > 1e-9
        or abs(pnl_total - pnl_daily) > 1e-9
    ):
        hint_roi += (
            f" | Patrimonio (treasury incluso): {roi_total:.3f}%"
            f" / {pnl_total:+.6f} ETH"
        )
    items.append(
        StatusItem(
            "ROI giornaliero (capitale)",
            f"{roi_daily:.3f}%",
            severity="info",
            hint=hint_roi,
        )
    )

    treasury_delta = _parse_float(last_log, "treasury_delta")
    if treasury_delta > 0:
        treasury_hint = f"Quota treasury prevista {treasury_delta:.6f} ETH"
    else:
        treasury_hint = "Nessun accredito treasury nell'ultimo ciclo"
    items.append(
        StatusItem(
            "Distribuzione treasury",
            f"{treasury_delta:.6f} ETH",
            severity="info",
            hint=treasury_hint,
        )
    )

    if state is not None:
        pool_id = state.get("pool_id") or "?"
        last_switch = state.get("last_switch_ts")
        if isinstance(last_switch, (int, float)) and last_switch > 0:
            ts = datetime.fromtimestamp(float(last_switch), timezone.utc)
            hint = _format_age(ts)
        else:
            hint = "nessuna rotazione registrata"
        items.append(
            StatusItem(
                "Ultimo switch efficace",
                str(pool_id),
                severity="info",
                hint=hint,
            )
        )

    return items


def _corrections_status(
    state: Dict[str, object] | None, last_log: Dict[str, str] | None
) -> List[StatusItem]:
    items: List[StatusItem] = []

    paused = bool(state.get("paused")) if state else False
    crisis_streak = int(state.get("crisis_streak", 0) or 0) if state else 0
    last_crisis = state.get("last_crisis_at") if state else None

    if paused:
        items.append(
            StatusItem(
                "Autopause",
                "Attiva",
                severity="error",
                hint="Riprendi manualmente il vault prima del prossimo deploy",
            )
        )
    else:
        severity = "warn" if crisis_streak > 0 else "ok"
        hint = f"streak crisi: {crisis_streak}" if crisis_streak else "operatività regolare"
        if last_crisis:
            hint += f" (ultimo evento {last_crisis})"
        items.append(
            StatusItem(
                "Autopause",
                "Non attiva",
                severity=severity,
                hint=hint,
            )
        )

    if last_log is None:
        return items

    status_raw = last_log.get("status", "")
    parts = status_raw.split("|") if status_raw else []
    head = parts[0] if parts else "(nessun dato)"
    tags = parts[1:] if len(parts) > 1 else []

    severity = "ok"
    if head.startswith("paused") or head.startswith("stopped"):
        severity = "error"
    elif head.startswith("SKIP"):
        severity = "warn"

    hint = ", ".join(tags) if tags else "nessun tag aggiuntivo"
    items.append(
        StatusItem(
            "Stato ultimo ciclo",
            head,
            severity=severity,
            hint=hint,
        )
    )

    # evidenzia tag sensibili (treasury, gas, skip portfolio)
    attention_tags: List[StatusItem] = []
    for tag in tags:
        if tag.startswith("treasury:"):
            severity_tag = "warn"
            if tag.endswith("disabled"):
                severity_tag = "info"
            elif tag.endswith("skipped"):
                severity_tag = "warn"
            attention_tags.append(
                StatusItem(
                    "Tesoreria",
                    tag,
                    severity=severity_tag,
                )
            )
        elif tag.startswith("gas"):
            attention_tags.append(
                StatusItem(
                    "Gas",
                    tag,
                    severity="warn",
                )
            )
        elif tag.startswith("portfolio") or tag.startswith("SKIP"):
            attention_tags.append(
                StatusItem(
                    "Portfolio",
                    tag,
                    severity="warn",
                )
            )

    items.extend(attention_tags)
    return items


def _collect_sections() -> List[Tuple[str, List[StatusItem]]]:
    state = _load_json(STATE_FILE) or {}
    last_log = _read_last_log_row(LOG_FILE)

    sections: List[Tuple[str, List[StatusItem]]] = [
        ("Deploy", _deploy_status(state or None)),
        ("Investment", _investment_status(state or None, last_log)),
        ("Corrections", _corrections_status(state or None, last_log)),
    ]
    return sections


def _sections_to_json(sections: List[Tuple[str, List[StatusItem]]]) -> Dict[str, List[Dict[str, object]]]:
    return {
        title.lower(): [item.to_dict() for item in items] for title, items in sections
    }


def _print_sections(sections: List[Tuple[str, List[StatusItem]]]) -> None:
    for title, rows in sections:
        print(f"=== {title} ===")
        for item in rows:
            icon = SEVERITY_ICON.get(item.severity, "•")
            line = f"{icon} {item.label}: {item.value}"
            if item.hint:
                line += f" — {item.hint}"
            print(line)
        print()


def _build_checklist(sections: List[Tuple[str, List[StatusItem]]]) -> List[str]:
    actionable: List[str] = []
    for title, items in sections:
        for item in items:
            if item.severity in {"warn", "error"}:
                entry = f"[{title}] {item.label}: {item.value}"
                if item.hint:
                    entry += f" — {item.hint}"
                actionable.append(entry)
    return actionable


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Valuta lo stato operativo della strategia Wave Rotation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Restituisce il report in formato JSON",
    )
    parser.add_argument(
        "--checklist",
        action="store_true",
        help="Mostra un riepilogo sintetico delle azioni mancanti",
    )
    args = parser.parse_args(argv)

    sections = _collect_sections()

    if args.json:
        payload = _sections_to_json(sections)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        _print_sections(sections)

    if args.checklist:
        entries = _build_checklist(sections)
        print("=== Checklist ===")
        if entries:
            for entry in entries:
                print(f"- {entry}")
        else:
            print("- Nessuna azione pendente ✅")


if __name__ == "__main__":
    main()
