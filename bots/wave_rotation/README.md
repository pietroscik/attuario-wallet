# Attuario Wave Rotation Bot

Implementazione della strategia “Wave Rotation” descritta in `CODEX_RULES.md`. Il bot effettua la rotazione giornaliera verso il pool con miglior score, applica la regola 50/50 (reinvest/treasury) e, se abilitato, registra l’esecuzione on-chain tramite `AttuarioVault.executeStrategy(string,uint256,uint256)`.

## Requisiti

- Python 3.10+
- Ambiente virtuale consigliato (`attuario/.venv`)
- Dipendenze: `pip install -r requirements.txt`

## Struttura

```
attuario/
├── .venv/
├── bots/
│   └── wave_rotation/
│       ├── strategy.py
│       ├── data_sources.py
│       ├── scoring.py
│       ├── executor.py
│       ├── logger.py
│       ├── onchain.py
│       ├── report.py
│       ├── config.json
│       └── requirements.txt
├── contracts/   # Hardhat project
└── scripts/
    └── run_daily.sh
```

## Configurazione

1. Copia `.env.example` in `.env` e valorizza le variabili (RPC, PRIVATE_KEY, TELEGRAM, ecc.).
2. Personalizza `bots/wave_rotation/config.json` se necessario (chains, min_tvl, ecc.).
3. Attiva l’ambiente virtuale e installa:

   ```
   cd attuario
   source .venv/bin/activate
   pip install -r bots/wave_rotation/requirements.txt
   ```

## Esecuzione manuale

```
cd attuario
source .venv/bin/activate
python3 bots/wave_rotation/strategy.py
python3 bots/wave_rotation/report.py

# Valutazione operativa

- Per un riepilogo rapido delle tre fasi (deploy, investimento, correzioni) esegui
  `python bots/wave_rotation/status_report.py`. Il comando legge i file locali
  (`state.json`, `log.csv`, `capital.txt`) e segnala gli aspetti da completare,
  evidenziando ad esempio quando la tesoreria automatica è disattivata
  (`TREASURY_AUTOMATION_ENABLED=false`).
```

Per schedulare via cron/Gelato usa `scripts/run_daily.sh` (che carica `.env` e redirige i log in `bots/wave_rotation/daily.log`).

## On-chain

- Abilita `ONCHAIN_ENABLED=true` (nel `.env`) e imposta `RPC_URL`, `PRIVATE_KEY`, `VAULT_ADDRESS`.
- Il bot calcola `apyBps = int(APY% * 100)` e `capital` in unità del token (default `CAPITAL_SCALE=1_000_000` per USDC) prima di chiamare `executeStrategy`.
- Ogni invio riuscito logga ed invia su Telegram l’hash di transazione.

## Treasury reale (EURC su Base)

- Per abilitare il trasferimento automatico imposta nel `.env`:
  - `TREASURY_AUTOMATION_ENABLED=true`
  - `TREASURY_ADDRESS=0xC8479c57f14D99Bf36E0efd48feDa746005Ce22d`
  - `TREASURY_TOKEN_ADDRESS=0xAdC42D37c9E07B440b0d0F15B93bb3f379f73d6c` (EURC)
  - opzionali: `SWAP_SLIPPAGE_BPS` (default 100 = 1%), `MIN_TREASURY_SWAP_ETH` (default 0.0005), `TREASURY_SWAP_API_KEY` se usi l’aggretatore 0x con API key.
- Quando il profitto giornaliero è positivo, il bot prova a swappare il 50% (quota treasury) da ETH → EURC tramite 0x Base API e trasferisce l’EURC all’indirizzo treasury.
- Se la funzione è disabilitata (variabili mancanti) la regola 50/50 resta simulata come prima e nel log compare `treasury:disabled`.

## Pool Configurati

La strategia ora supporta **15 pool** su Base chain, coprendo tutti i principali settori DeFi:

- **4 Aave v3 Lending**: WETH, USDC, cbBTC, cbETH
- **5 Beefy/Aerodrome LP**: USDC/cbBTC, USDC/USDT (stable), WETH/USDC, cbETH/WETH (LST), WETH/USDT
- **3 ERC-4626 Vaults**: WETH yield, cbBTC vault, USDC vault
- **1 Yearn Vault**: Yearn USDC su Base
- **2 Mercati Compound-based**: Comet USDC (Compound v3) e Moonwell cbETH (cToken)

Per configurare i nuovi pool:

1. **Verifica configurazione**:
   ```bash
   python3 validate_pools.py
   ```

2. **Imposta indirizzi mancanti** nel `.env` (vedi `.env.example` per la lista completa):
   - Token addresses (USDT, cbETH, WETH)
   - Beefy vault addresses
   - ERC-4626 vault addresses
   - Yearn vault addresses
   - Mercati Compound (Comet) e Moonwell cToken

3. **Documentazione completa**:
   - `POOLS.md` - Descrizione dettagliata di tutti i pool
   - `POOL_SETUP.md` - Guida passo-passo alla configurazione

4. **Test configurazione**:
   ```bash
   python3 test_pools.py
   ```

## Allocazione automatica verso i pool

- Definisci nel `config.json` la sezione `adapters` con la mappatura `pool_id → adapter`.

  ```json
  "adapters": {
    "pool:base:aave-v3:USDC": {
      "type": "aave_v3",
      "pool": "${AAVE_POOL_ADDRESS_8453}",
      "asset": "${USDC_BASE}",
      "decimals": 6
    },
    "pool:base:beefy:USDC-USDT": {
      "type": "lp_beefy_aero",
      "router": "${AERODROME_ROUTER_8453}",
      "beefy_vault": "${BEEFY_USDC_USDT_VAULT}",
      "token0": "${USDC_BASE}",
      "token1": "${USDT_BASE}",
      "stable": true,
      "slippage_bps": 30
    }
  }
  ```

- Attiva l’automazione impostando `PORTFOLIO_AUTOMATION_ENABLED=true` nel `.env`.
- Facoltativo: `PORTFOLIO_DRY_RUN=true` per simulare withdraw/deposit senza inviare transazioni (utile nei test).
- Ad oggi sono supportati gli adapter espliciti `erc4626`, `aave_v3`, `lp_beefy_aero`, `yearn`, `comet` e `ctoken`. Altri protocolli possono essere aggiunti estendendo `bots/wave_rotation/adapters/`.
- Se non esiste un adapter esplicito, il bot prova gli auto-adapter (ERC-4626, Beefy/Yearn, Compound v2/v3, Aave v3) con caching (`cache/auto_adapter_cache.json`). Se nessuno è compatibile, il pool viene saltato senza spese di gas.
- Guardrail operativi (tutti opzionali, nel `.env`):
  - `GAS_PRICE_MAX_GWEI` per saltare i movimenti quando il gas supera la soglia.
  - `MIN_EDGE_SCORE`, `MIN_EDGE_ETH`, `MIN_EDGE_USD` (+ `ETH_PRICE_USD`) per richiedere un delta di score minimo, un guadagno previsto in ETH o USD prima di muovere capitale.
  - `EDGE_GAS_MULTIPLIER` per richiedere che il guadagno stimato superi il costo gas moltiplicato per il fattore indicato.
  - `SWITCH_COOLDOWN_S` per imporre un minimo intervallo tra due rotazioni effettive.
  - `ALLOWANCE_MODE=MAX|EXACT` controlla se impostare allowance infinita o puntuale sull’asset sottostante.
  - `MAX_WRAP_PCT` (default 0.8) limita la quota di ETH convertibile in WETH durante i depositi auto.
- Dati DefiLlama: di default il bot usa l’endpoint gratuito `https://yields.llama.fi` (nessuna chiave necessaria). Se preferisci il cluster Pro, imposta `DEFILLAMA_API=https://pro-api.llama.fi` e `DEFILLAMA_API_KEY=<chiave>`; in assenza di chiave il codice ricade automaticamente sul dominio free (`https://api.llama.fi`).

## Loop operativo

- Usa `scripts/run_wave_rotation_loop.sh` per un loop continuo: carica `.env` (incluso `WAVE_LOOP_INTERVAL_SECONDS`, default 3600s) e scrive i log in `bots/wave_rotation/daily.log`.
- Lo stop-loss giornaliero di default è -5% (`stop_loss_daily` in `config.json`); aggiorna il file se vuoi un’altra soglia.
