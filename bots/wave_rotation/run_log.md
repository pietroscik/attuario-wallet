# Wave Rotation – Esecuzione del 2025-10-26

- Fonte dati: endpoint mock locale (`http://127.0.0.1:9000/pools`) con 3 pool di test.
- RPC: mock JSON-RPC locale su `http://127.0.0.1:8545` per superare i controlli di connettività.
- Parametri principali: `PORTFOLIO_AUTOMATION_ENABLED=true`, `PORTFOLIO_DRY_RUN=true`, `ONCHAIN_ENABLED=false`.
- Risultato selezione: pool `alpha-ETH-USDC` (chain `base`) con score 0.000311.
- Capitale prima/dopo: 100.000000 ETH → 100.000321 ETH.
- Treasury pianificata: +0.000321 ETH (in dry-run).
- Stato finale: `executed` con note `portfolio:onchain_disabled`, `treasury:disabled`.
- File log aggiornati: `bots/wave_rotation/log.csv`, `capital.txt`, `treasury.txt`, `state.json` (tutti ignorati dal VCS).

L'esecuzione è stata validata dal comando `python3 bots/wave_rotation/status_report.py`, che conferma capitale aggiornato e quota treasury simulata.
