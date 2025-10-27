# Stato di allineamento a CODEX_RULES

L'ultima iterazione del bot di rotazione è stata aggiornata per aderire ai requisiti esplicitati in CODEX_RULES.
Di seguito un riepilogo delle aree principali.

## 1. Ciclo operativo
- L'intervallo di polling di default torna a 5 minuti (`WAVE_LOOP_INTERVAL_SECONDS`), come previsto dal mandato.
- Restano disponibili gli override via variabile d'ambiente, ma il minimo effettivo rimane 300 secondi.

## 2. Calcolo di rendimento, costi e score
- `select_best_pool` calcola `r_day`, `r_net` e lo score direttamente con la formula `r / (1 + c · (1 − ρ))`, usando il costo giornaliero così come fornito dalla sorgente (`fee_pct`).
- Il costo non viene più diviso per 365, eliminando la distorsione sui punteggi e sul rendimento netto.
- Il modulo `scoring.py` espone funzioni coerenti con CODEX_RULES e non applica penalità additive basate su staleness, TVL o provenienza dell'adapter.

## 3. Selezione dei pool
- L'unico filtro applicato è `tvl_usd >= min_tvl_usd` (100k USD di default); non esistono più blacklist, gating sugli adapter, né filtri impliciti su token "virtuali".
- Il ranking è un semplice ordinamento per score. L'esecuzione finale (`ops_guard.should_move`) richiede soltanto che il delta di score sia positivo e che il guadagno atteso superi il costo gas stimato (configurabile via `.env`).

## 4. Stato residuo
- L'autopause continua a rispettare le impostazioni del file di configurazione (`autopause.streak`, `resume_wait_minutes`, ecc.), in linea con la sezione 5 delle regole.
- L'esecuzione on-chain richiede ancora la disponibilità di adapter espliciti o automatici (`executor.move_capital_smart`), condizione inevitabile per effettuare depositi/prelievi reali.

Con queste modifiche la pipeline di analisi, ranking e switch rispetta il perimetro funzionale definito da CODEX_RULES, mantenendo soltanto i guardrail strettamente necessari all'esecuzione su chain.
