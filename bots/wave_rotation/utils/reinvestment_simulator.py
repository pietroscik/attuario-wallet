"""Utility per simulare e rendicontare la dinamica di reinvestimento della strategia.

Questo script riproduce fedelmente la logica descritta nelle specifiche operative:
- Il capitale resta completamente investito (nessuna quota inattiva).
- A fine ciclo il rendimento lordo viene diviso 50/50 solo se la quota di
  tesoreria eccede la soglia minima in EUR; altrimenti viene reinvestito al 100%.
- L'APY effettivo è calcolato come prodotto cumulativo dei rendimenti netti
  reinvestiti (∏ (1 + r_netto_i) − 1).

Può lavorare in due modalità:
1. ``simulate``: simula una sequenza di cicli partendo da un capitale iniziale.
2. ``analyze-log``: analizza il ``log.csv`` prodotto dal bot e ricostruisce i
   rendimenti effettivi di ogni ciclo.

L'output può essere reso in formato tabellare leggibile oppure in JSON.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

# Valori di default coerenti con strategy.py
DEFAULT_FX_EUR_PER_ETH = 3000.0
DEFAULT_TREASURY_MIN_EUR = 0.5
DEFAULT_BASE_REINVEST_RATIO = 0.5


try:  # Prova a riutilizzare l'implementazione ufficiale
    from bots.wave_rotation.strategy import effective_reinvest_ratio as _strategy_ratio
except Exception:  # pragma: no cover - fallback per esecuzioni standalone
    _strategy_ratio = None


@dataclass
class CycleResult:
    """Risultato di un ciclo giornaliero."""

    index: int
    capital_before: float
    r_net: float
    profit: float
    reinvest_ratio: float
    reinvested: float
    treasury_add: float
    capital_after: float
    treasury_total: float

    @property
    def net_reinvest_rate(self) -> float:
        if self.capital_before <= 0:
            return 0.0
        return (self.capital_after - self.capital_before) / self.capital_before

    def as_dict(self) -> dict:
        data = {
            "cycle": self.index,
            "capital_before": self.capital_before,
            "r_net": self.r_net,
            "profit": self.profit,
            "reinvest_ratio": self.reinvest_ratio,
            "reinvested": self.reinvested,
            "treasury_add": self.treasury_add,
            "capital_after": self.capital_after,
            "treasury_total": self.treasury_total,
            "net_reinvest_rate": self.net_reinvest_rate,
        }
        return data


def _effective_reinvest_ratio(
    profit_eth: float,
    base_ratio: float,
    *,
    fx_rate: float,
    min_payout_eur: float,
) -> float:
    """Replica la logica di ``strategy.effective_reinvest_ratio``.

    Se disponibile riutilizza la funzione originale, altrimenti applica la
    formula localmente (utile quando lo script viene eseguito standalone).
    """

    if _strategy_ratio is not None:  # pragma: no branch - percorso principale
        return _strategy_ratio(
            profit_eth,
            base_ratio,
            fx_rate=fx_rate,
            min_payout_eur=min_payout_eur,
        )

    if profit_eth <= 0:
        return 1.0

    base = max(0.0, min(1.0, base_ratio))
    treasury_ratio = 1.0 - base
    if treasury_ratio <= 0:
        return 1.0

    fx_rate = max(fx_rate, 0.0)
    min_payout_eur = max(min_payout_eur, 0.0)
    treasury_share_eur = profit_eth * treasury_ratio * fx_rate
    if treasury_share_eur >= min_payout_eur:
        return base
    return 1.0


def run_simulation(
    initial_capital: float,
    returns: Sequence[float],
    *,
    base_reinvest_ratio: float = DEFAULT_BASE_REINVEST_RATIO,
    fx_rate: float = DEFAULT_FX_EUR_PER_ETH,
    min_payout_eur: float = DEFAULT_TREASURY_MIN_EUR,
) -> List[CycleResult]:
    """Simula una sequenza di cicli della strategia."""

    capital = float(initial_capital)
    treasury = 0.0
    results: List[CycleResult] = []

    for idx, r_net in enumerate(returns, start=1):
        profit = capital * r_net
        reinvest_ratio = (
            _effective_reinvest_ratio(
                profit,
                base_reinvest_ratio,
                fx_rate=fx_rate,
                min_payout_eur=min_payout_eur,
            )
            if profit > 0
            else 1.0
        )
        reinvested = reinvest_ratio * profit
        treasury_add = profit - reinvested if profit > 0 else 0.0
        capital_after = capital + reinvested
        treasury = treasury + max(treasury_add, 0.0)

        result = CycleResult(
            index=idx,
            capital_before=capital,
            r_net=r_net,
            profit=profit,
            reinvest_ratio=reinvest_ratio,
            reinvested=reinvested,
            treasury_add=treasury_add,
            capital_after=capital_after,
            treasury_total=treasury,
        )
        results.append(result)
        capital = capital_after

    return results


def load_cycles_from_log(path: Path) -> List[CycleResult]:
    """Carica i cicli effettivi dal ``log.csv`` della strategia."""

    if not path.exists():
        raise FileNotFoundError(f"Log non trovato: {path}")

    with path.open("r", newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"capital_before", "capital_after"}
        if not required.issubset(reader.fieldnames or {}):
            missing = required.difference(reader.fieldnames or set())
            raise ValueError(f"Colonne mancanti nel log: {', '.join(sorted(missing))}")

        results: List[CycleResult] = []
        treasury_total = 0.0
        for idx, row in enumerate(reader, start=1):
            try:
                capital_before = float(row["capital_before"])
                capital_after = float(row["capital_after"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Valori numerici invalidi alla riga {idx}: {exc}") from exc

            treasury_add = float(row.get("treasury_delta") or 0.0)
            r_net = float(row.get("r_net_interval") or row.get("r_net_daily") or 0.0)
            reinvested = capital_after - capital_before
            profit = reinvested + treasury_add
            reinvest_ratio = (
                (reinvested / profit) if profit > 0 else 1.0
            )
            treasury_total += max(treasury_add, 0.0)

            results.append(
                CycleResult(
                    index=idx,
                    capital_before=capital_before,
                    r_net=r_net,
                    profit=profit,
                    reinvest_ratio=reinvest_ratio,
                    reinvested=reinvested,
                    treasury_add=max(treasury_add, 0.0),
                    capital_after=capital_after,
                    treasury_total=treasury_total,
                )
            )

    return results


def summarize_cycles(cycles: Iterable[CycleResult]) -> dict:
    """Produce statistiche aggregate sui cicli."""

    cycles = list(cycles)
    if not cycles:
        return {
            "cycles": 0,
            "capital_start": 0.0,
            "capital_end": 0.0,
            "treasury_total": 0.0,
            "apy_effective": 0.0,
            "weighted_reinvest_ratio": 1.0,
        }

    reinvest_rates = [c.net_reinvest_rate for c in cycles]
    apy_effective = math.prod(1.0 + rate for rate in reinvest_rates) - 1.0

    total_profit_positive = sum(max(c.profit, 0.0) for c in cycles)
    total_reinvested_positive = sum(max(c.reinvested, 0.0) for c in cycles)
    weighted_reinvest_ratio = (
        total_reinvested_positive / total_profit_positive
        if total_profit_positive > 0
        else 1.0
    )

    summary = {
        "cycles": len(cycles),
        "capital_start": cycles[0].capital_before,
        "capital_end": cycles[-1].capital_after,
        "treasury_total": cycles[-1].treasury_total,
        "apy_effective": apy_effective,
        "weighted_reinvest_ratio": weighted_reinvest_ratio,
    }
    return summary


def _format_float(value: float) -> str:
    return f"{value:.6f}"


def render_table(cycles: Sequence[CycleResult]) -> str:
    """Crea una tabella testuale con i risultati dei cicli."""

    headers = [
        "cycle",
        "capital_before",
        "r_net",
        "profit",
        "reinvest_ratio",
        "reinvested",
        "treasury_add",
        "capital_after",
        "treasury_total",
        "net_reinvest_rate",
    ]

    rows = []
    for c in cycles:
        rows.append([
            str(c.index),
            _format_float(c.capital_before),
            _format_float(c.r_net),
            _format_float(c.profit),
            _format_float(c.reinvest_ratio),
            _format_float(c.reinvested),
            _format_float(c.treasury_add),
            _format_float(c.capital_after),
            _format_float(c.treasury_total),
            _format_float(c.net_reinvest_rate),
        ])

    widths = [len(h) for h in headers]
    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def _format_line(items: Sequence[str]) -> str:
        return " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(items))

    sep = "-+-".join("-" * width for width in widths)
    lines = [_format_line(headers), sep]
    for row in rows:
        lines.append(_format_line(row))

    return "\n".join(lines)


def parse_returns(raw: str) -> List[float]:
    """Parsa una lista di rendimenti in formato ``0.01,0.005``."""

    if not raw:
        raise ValueError("Specificare almeno un rendimento")
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if not parts:
        raise ValueError("Lista di rendimenti vuota")
    returns: List[float] = []
    for part in parts:
        try:
            returns.append(float(part))
        except ValueError as exc:
            raise ValueError(f"Rendimento non numerico: {part}") from exc
    return returns


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    simulate_parser = subparsers.add_parser("simulate", help="Simula una sequenza di cicli")
    simulate_parser.add_argument("--capital", type=float, required=True, help="Capitale iniziale (ETH)")
    simulate_parser.add_argument(
        "--returns",
        type=str,
        required=True,
        help="Rendimenti netti del ciclo (decimali, separati da virgola)",
    )
    simulate_parser.add_argument("--base-ratio", type=float, default=DEFAULT_BASE_REINVEST_RATIO)
    simulate_parser.add_argument("--fx-rate", type=float, default=DEFAULT_FX_EUR_PER_ETH)
    simulate_parser.add_argument("--min-eur", type=float, default=DEFAULT_TREASURY_MIN_EUR)
    simulate_parser.add_argument(
        "--json",
        action="store_true",
        help="Restituisce i risultati in formato JSON invece che tabellare",
    )

    log_parser = subparsers.add_parser("analyze-log", help="Analizza il log CSV della strategia")
    log_parser.add_argument(
        "--log-file",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "log.csv",
        help="Percorso del log (default: bots/wave_rotation/log.csv)",
    )
    log_parser.add_argument(
        "--json",
        action="store_true",
        help="Restituisce i risultati in formato JSON invece che tabellare",
    )

    args = parser.parse_args(argv)

    if args.command == "simulate":
        returns = parse_returns(args.returns)
        cycles = run_simulation(
            initial_capital=args.capital,
            returns=returns,
            base_reinvest_ratio=args.base_ratio,
            fx_rate=args.fx_rate,
            min_payout_eur=args.min_eur,
        )
    else:
        cycles = load_cycles_from_log(args.log_file)

    summary = summarize_cycles(cycles)

    if args.json:
        payload = {
            "cycles": [cycle.as_dict() for cycle in cycles],
            "summary": summary,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(render_table(cycles))
        print()
        print(json.dumps(summary, indent=2))

    return 0


if __name__ == "__main__":  # pragma: no cover - entrypoint CLI
    raise SystemExit(main())
