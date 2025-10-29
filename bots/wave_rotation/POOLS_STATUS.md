# Pools Status and Execution Guide

## ✅ Pools Ready to Execute (21/21)

Tutte le configurazioni su Base sono state validate con `validate_pools.py` (21/21 ready). Di seguito il dettaglio per categoria.

### Aave v3 Lending (4 pool)
1. **pool:base:aave-v3:WETH** — Lending WETH su Aave v3  
2. **pool:base:aave-v3:USDC** — Lending USDC su Aave v3  
3. **pool:base:aave-v3:cbBTC** — Lending cbBTC su Aave v3  
4. **pool:base:aave-v3:cbETH** — Lending cbETH su Aave v3  

### Beefy/Aerodrome LP (5 pool)
1. **pool:base:beefy:USDC-cbBTC** — Vault Beefy USDC/cbBTC  
2. **pool:base:beefy:USDC-USDT** — Vault stable/stable (`stable: true`)  
3. **pool:base:beefy:WETH-USDC** — Vault ETH/stable principale  
4. **pool:base:beefy:cbETH-WETH** — Vault LST cbETH/WETH  
5. **pool:base:beefy:WETH-USDT** — Vault ETH/stable alternativo  

Gli indirizzi dei vault `BEEFY_*_VAULT` vengono risolti dagli script in `scripts/resolve_beefy_vaults.sh` e salvati in `.env` / GitHub Environment.

### ERC-4626 & Morpho Vaults (5 pool)
1. **pool:base:erc4626:WETH-yield** — Vault WETH autocompound (Morpho × Yearn)  
2. **pool:base:erc4626:cbBTC-vault** — Vault ERC-4626 su cbBTC  
3. **pool:base:erc4626:USDC-vault** — Vault ERC-4626 su USDC  
4. **pool:base:morpho:USDC** — Morpho Blue USDC (interface ERC-4626)  
5. **pool:base:morpho:WETH** — Morpho Blue WETH (interface ERC-4626)  

Gli script `resolve_erc4626_vaults.sh` e `resolve_compound_markets.sh` popolano le variabili corrispondenti (`WETH_YIELD_VAULT_BASE`, `CBBTC_ERC4626_VAULT`, `MORPHO_*`).

### Yearn Vaults (2 pool)
1. **pool:base:yearn:USDC** — Vault Yearn USDC su Base  
2. **pool:base:yearn:WETH** — Vault Yearn WETH su Base  

Gli indirizzi vengono recuperati da `resolve_yearn_vaults.sh` via API yDaemon.

### Compound v3 (Comet) Markets (2 pool)
1. **pool:base:comet:USDC** — Mercato Comet USDC  
2. **pool:base:comet:USDbC** — Mercato Comet USDbC (legacy stablecoin)  

Gli address `COMET_*` sono risolti automaticamente (`resolve_compound_markets.sh`).

### Moonwell cToken Markets (3 pool)
1. **pool:base:moonwell:cbETH** — cToken cbETH (Moonwell Base)  
2. **pool:base:moonwell:WETH** — cToken WETH  
3. **pool:base:moonwell:USDC** — cToken USDC  

Gli address `MOONWELL_*_CTOKEN` sono anch’essi popolati dai workflow/script.

## Environment Recap

- `.env.example` contiene tutti i token address di Base (`USDC_BASE`, `USDBC_BASE`, `CBETH_BASE`, ecc.).  
- Gli script di risoluzione (`scripts/resolve_*.sh`) valorizzano Beefy, Yearn, Morpho, Comet e Moonwell.  
- In caso di failure API, è possibile impostare manualmente le variabili in `.env` o nei secret GitHub; la strategia continua comunque a funzionare con i valori già presenti.

## Running the Strategy

```bash
cd bots/wave_rotation

# 1. Popola/aggiorna le variabili (se necessario)
./scripts/resolve_beefy_vaults.sh
./scripts/resolve_yearn_vaults.sh
./scripts/resolve_compound_markets.sh
./scripts/resolve_erc4626_vaults.sh

# 2. Valida la configurazione
python3 validate_pools.py  # => Summary: 21/21 pools ready

# 3. Esegui i test di coerenza
python3 test_pools.py

# 4. Avvia la strategia
python3 strategy.py
```

## Strategy Behavior

La Wave Rotation strategy:
- Valuta i 21 pool configurati, calcola score e rischio per ciascuno
- Ordina per score e seleziona il migliore
- Applica uno switch solo se il nuovo score è ≥1% rispetto all’attuale
- Reinveste il 50% dei profitti e invia il restante 50% alla treasury

## Copertura di Mercato

- **Lending**: Aave v3 (4), Morpho (2), Comet (2), Moonwell (3)
- **LP Farming**: Beefy + Aerodrome (5)
- **Vault Strategies**: ERC-4626 (5) + Yearn (2)
- **Stable/Stable**: USDC/USDT
- **ETH/Stables**: WETH/USDC, WETH/USDT
- **LST**: cbETH/WETH, cbETH lending
- **BTC**: cbBTC lending, vault, LP
- **Legacy Stable**: USDbC via Comet

## Monitoring

- I workflow GitHub eseguono gli script di risoluzione a ogni run.  
- `status_report.py` e `run_log.md` permettono di verificare gli switch effettuati.  
- In caso di nuovi vault/mercati, aggiungere le chiavi corrispondenti e rilanciare gli script per mantenerle aggiornate.
