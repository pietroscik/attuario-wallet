#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Report serale 📊 – Strategia Attuario Wave Rotation."""

import os
from pathlib import Path
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import requests
from dotenv import load_dotenv

# === CONFIG ===
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHATID = os.getenv("TELEGRAM_CHATID")
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "log.csv"
IMG_FILE = BASE_DIR / "report.png"


# === TELEGRAM ===
def send_telegram_photo(photo_path, caption):
    """Invia foto con didascalia su Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHATID:
        print("[!] Telegram non configurato")
        return
    try:
        with open(photo_path, "rb") as img:
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                data={"chat_id": TELEGRAM_CHATID, "caption": caption},
                files={"photo": img}
            )
        if not r.ok:
            print("[!] Errore Telegram:", r.json())
    except Exception as e:
        print("[!] Errore Telegram:", e)


# === PLOT ===
def generate_plot():
    """Genera grafico capitale + media mobile 7 giorni"""
    if not LOG_FILE.exists():
        print("[!] Nessun log trovato")
        return None, None, None

    df = pd.read_csv(LOG_FILE, sep=None, engine="python", on_bad_lines="skip")

    # rileva nome colonna capitale
    if "capital_after" not in df.columns:
        print("[!] Colonna capital_after mancante nel log")
        return None, None, None
    cap_col = "capital_after"

    # parsing e ordinamento
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", cap_col]).sort_values("date")

    # media mobile 7 giorni
    df["ma7"] = df[cap_col].rolling(window=7, min_periods=1).mean()

    # grafico
    plt.figure(figsize=(8, 4))
    plt.plot(df["date"], df[cap_col], marker="o", color="tab:blue",
             label="Capitale giornaliero")
    plt.plot(df["date"], df["ma7"], color="deepskyblue", linewidth=2,
             label="Media mobile 7 gg")
    plt.title("📊 Andamento del Capitale – Strategia 💯 Equilibrato")
    plt.xlabel("Data")
    plt.ylabel("Capitale (€)")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(IMG_FILE, dpi=200)
    plt.close()

    return df, IMG_FILE, cap_col


# === MAIN ===
def main():
    df, img, cap_col = generate_plot()
    if df is None:
        return

    numeric_cols = [
        "r_net_daily",
        "r_net_interval",
        "r_realized",
        "roi_daily",
        "roi_total",
        "pnl_daily",
        "pnl_total",
        "score",
        "treasury_delta",
        "capital_before",
        "capital_after",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    cap_now = float(latest[cap_col])
    cap_prev = float(prev[cap_col]) if prev is not None else cap_now
    delta = ((cap_now - cap_prev) / cap_prev) * 100 if cap_prev else 0

    mean_rend = df["r_net_interval"].mean() * 100 if "r_net_interval" in df.columns else delta
    treasury = float(df["treasury_delta"].sum()) if "treasury_delta" in df.columns else 0.0

    best = df.sort_values("score", ascending=False).iloc[0] if "score" in df.columns else latest

    msg = (
        f"📊 Riepilogo giornaliero – {datetime.now().strftime('%d %b %Y')}\n"
        f"💰 Capitale: {cap_now:.6f} ETH ({delta:+.2f}%)\n"
        f"📈 r_net medio: {mean_rend:.4f}%\n"
        f"🏦 Treasury cumulato: {treasury:.6f} ETH\n"
        f"🥇 Miglior score: {best['pool']} ({best['score']:.6f})"
    )

    print(msg)
    send_telegram_photo(img, msg)


# === ESECUZIONE ===
if __name__ == "__main__":
    main()
