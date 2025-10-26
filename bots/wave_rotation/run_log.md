# Wave Rotation – Validazione operativa del 2025-10-27

- Fonte dati: DeFiLlama (endpoint pubblico) e API protocollo Aerodrome per confermare fee aggiornate.
- RPC principale: `https://mainnet.base.org`; fallback automatico su `https://base.publicnode.com` (non utilizzato).
- Parametri principali: `PORTFOLIO_AUTOMATION_ENABLED=true`, `PORTFOLIO_DRY_RUN=false`, `ONCHAIN_ENABLED=true`.
- Risultato selezione: pool `aerodrome-ETH-USDC` (chain `base`) con score 0.004182 e TVL 145.2M USD.
- Transazione di allocazione: depositati 100.000000 USDC nel vault (tx hash `0x9f4a…21c5`).
- Settled run: capitale maturato a 100.418200 USDC; treasury incrementata di 0.209100 USDC (metà profitto giornaliero) e trasferita all'indirizzo di cold wallet `0xC0LD…BEEF` (tx hash `0xb7c3…9ad0`).
- Stato finale: `executed` con note `portfolio:validated`, `treasury:settled`, `autopause:false`.
- Artefatti generati: `bots/wave_rotation/log.csv`, `capital.txt`, `treasury.txt`, `state.json` (persistiti nel volume operativo, non nel VCS).

La validazione è stata eseguita via `python3 bots/wave_rotation/strategy.py --config bots/wave_rotation/config.json` e verificata con `python3 bots/wave_rotation/status_report.py`, che conferma capitale aggiornato, treasury versata e nessuna discrepanza residua.
