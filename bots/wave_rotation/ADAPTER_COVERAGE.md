# Adapter Coverage Documentation

## Overview

Il sistema di Attuario Wallet utilizza adapter per interagire con diversi protocolli DeFi. Gli adapter si dividono in due categorie:

1. **Adapter Espliciti** (`adapters/`): Configurati manualmente nel file `config.json`
2. **Adapter Automatici** (`adapters_auto/`): Rilevati automaticamente tramite probing on-chain

## Adapter Automatici Supportati

### 1. ERC-4626 Vaults (`erc4626_auto.py`)
Standard vault interface per strategie di yield.

**Protocolli compatibili:**
- Morpho Blue Vaults
- Vaults standard ERC-4626
- Sommelier Vaults
- Yearn V3 (ERC-4626 compatible)

**Funzionalità:**
- ✅ Auto-wrap ETH → WETH quando necessario
- ✅ Deposit di tutti i fondi disponibili
- ✅ Redeem completo tramite `maxRedeem`
- ✅ Gestione automatica delle approvazioni

**Probe:** Verifica presenza della funzione `asset()`

### 2. Morpho Blue Vaults (`morpho_auto.py`)
Specializzato per Morpho Blue, ma compatibile con ERC-4626.

**Caratteristiche:**
- Stesso comportamento di ERC4626Auto
- Ottimizzato per Morpho Blue vaults
- Supporta curator-managed strategies

**Indirizzi su Base:**
- USDC Vault: `0xef417a2512C5a41f69AE4e021648b69a7CdE5D03`
- WETH Vault: `0x38989BBA00BDF8181F4082995b3DEAe96163aC5D`

### 3. Beefy Finance (`beefy_auto.py`)
Auto-compounding vault per liquidity provision.

**Funzionalità:**
- ✅ Deposit in Beefy vaults
- ✅ Auto-wrap per asset nativi
- ✅ Withdraw completo

**Probe:** Verifica presenza della funzione `want()`

**Risoluzione automatica:** Script `scripts/resolve_beefy_vaults.sh` cerca vaults su Base via API Beefy

### 4. Yearn Finance (`yearn_auto.py`)
Vaults Yearn V2/V3 compatibili.

**Funzionalità:**
- ✅ Deposit in Yearn vaults
- ✅ Withdraw completo
- ✅ Supporto multi-versione (V2/V3)

**Probe:** Verifica presenza della funzione `token()`

**Risoluzione automatica:** Script `scripts/resolve_yearn_vaults.sh` cerca vaults su Base via API Yearn

### 5. Aave V3 (`aavev3_auto.py`)
Lending protocol Aave V3.

**Funzionalità:**
- ✅ Supply asset → ricevi aToken
- ✅ Withdraw completo tramite pool
- ✅ Auto-wrap per asset nativi
- ✅ Gestione approvazioni

**Probe:** Verifica presenza della funzione `UNDERLYING_ASSET_ADDRESS()` (aToken)

**Configurazione richiesta:**
```bash
AAVE_POOL_ADDRESS_8453=0xA238Dd80C259a72e81d7e4664a9801593F98d1c5
```

### 6. Compound V3 / Comet (`comet_auto.py`)
Mercati Compound V3 (Comet).

**Funzionalità:**
- ✅ Supply su mercati Comet
- ✅ Withdraw completo
- ✅ Auto-wrap per asset nativi

**Probe:** Verifica presenza della funzione `baseToken()`

**Indirizzi su Base:**
- USDC Market: `0x46e6b214b524310239732D51387075E0e70970bf`
- USDbC Market: `0x9c4ec768c28520B50860ea7a15bd7213a9fF58bf`

### 7. Compound V2 / Moonwell (`ctoken_auto.py`)
cToken per Compound V2 e fork (Moonwell).

**Funzionalità:**
- ✅ Mint cToken tramite deposit
- ✅ Redeem completo
- ✅ Auto-wrap per asset nativi

**Probe:** Verifica presenza della funzione `underlying()`

**Indirizzi Moonwell su Base:**
- cbETH: `0x3bf93770f2d4a794c3d9EBEfBAeBAE2a8f09A5E5`
- WETH: `0x628ff693426583D9a7FB391E54366292F509D457`
- USDC: `0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22`

### 8. Sonne Finance (`sonne_auto.py`)
Fork di Compound V2 per Optimism.

**Funzionalità:**
- Stesso comportamento di CTokenAuto
- Ottimizzato per Sonne Finance su Optimism

**Probe:** Verifica `underlying()` + `comptroller()`

## Adapter Espliciti

Gli adapter espliciti richiedono configurazione manuale in `config.json`:

### 1. Aave V3 (`adapters/aave_v3.py`)
Versione esplicita per controllo granulare.

**Configurazione:**
```json
{
  "type": "aave_v3",
  "pool": "${AAVE_POOL_ADDRESS_8453}",
  "asset": "${WETH_TOKEN_ADDRESS}",
  "decimals": 18
}
```

### 2. ERC-4626 (`adapters/erc4626.py`)
Versione esplicita per vaults specifici.

**Configurazione:**
```json
{
  "type": "erc4626",
  "vault": "${USDC_ERC4626_VAULT}",
  "asset": "${USDC_BASE}"
}
```

### 3. Yearn (`adapters/yearn.py`)
Versione esplicita per Yearn vaults.

**Configurazione:**
```json
{
  "type": "yearn",
  "vault": "${YEARN_USDC_VAULT_BASE}",
  "asset": "${USDC_BASE}"
}
```

### 4. Comet (`adapters/comet.py`)
Versione esplicita per Compound V3.

**Configurazione:**
```json
{
  "type": "comet",
  "market": "${COMET_USDC_MARKET_BASE}",
  "asset": "${USDC_BASE}"
}
```

### 5. CToken (`adapters/ctoken.py`)
Versione esplicita per cToken.

**Configurazione:**
```json
{
  "type": "ctoken",
  "ctoken": "${MOONWELL_CBETH_CTOKEN}",
  "asset": "${CBETH_BASE}"
}
```

### 6. Beefy/Aerodrome LP (`adapters/lp_beefy_aero.py`)
Liquidity provision su Aerodrome con farming su Beefy.

**Configurazione:**
```json
{
  "type": "lp_beefy_aero",
  "router": "${AERODROME_ROUTER_8453}",
  "beefy_vault": "${BEEFY_WETH_USDC_VAULT}",
  "token0": "${WETH_TOKEN_ADDRESS}",
  "token1": "${USDC_BASE}",
  "slippage_bps": 50
}
```

## Script di Risoluzione Automatica

Per popolare automaticamente le variabili d'ambiente dei protocolli:

### 1. Beefy Vaults (`scripts/resolve_beefy_vaults.sh`)
Cerca vaults Beefy su Base via API ufficiale.

**Utilizzo:**
```bash
./scripts/resolve_beefy_vaults.sh
```

**Variabili popolate:**
- `BEEFY_USDC_USDT_VAULT`
- `BEEFY_WETH_USDC_VAULT`
- `BEEFY_WETH_USDT_VAULT`
- `BEEFY_CBETH_WETH_VAULT`

### 2. Yearn Vaults (`scripts/resolve_yearn_vaults.sh`)
Cerca vaults Yearn su Base via API ufficiale.

**Utilizzo:**
```bash
./scripts/resolve_yearn_vaults.sh
```

**Variabili popolate:**
- `YEARN_USDC_VAULT_BASE`
- `YEARN_WETH_VAULT_BASE`
- `YEARN_CBBTC_VAULT_BASE`

### 3. Compound/Moonwell (`scripts/resolve_compound_markets.sh`)
Imposta indirizzi ufficiali di Compound V3 e Moonwell.

**Utilizzo:**
```bash
./scripts/resolve_compound_markets.sh
```

**Variabili popolate:**
- `COMET_USDC_MARKET_BASE`
- `COMET_USDBC_MARKET_BASE`
- `MOONWELL_CBETH_CTOKEN`
- `MOONWELL_WETH_CTOKEN`
- `MOONWELL_USDC_CTOKEN`

### 4. ERC-4626 Vaults (`scripts/resolve_erc4626_vaults.sh`)
Imposta indirizzi di vaults ERC-4626 verificati.

**Utilizzo:**
```bash
./scripts/resolve_erc4626_vaults.sh
```

**Variabili popolate:**
- `USDC_ERC4626_VAULT`
- `WETH_ERC4626_VAULT`

## Workflow GitHub Actions

Il workflow `.github/workflows/run-strategy.yml` esegue automaticamente tutti gli script di risoluzione:

```yaml
- name: Resolve Beefy vaults (Base)
  run: scripts/resolve_beefy_vaults.sh

- name: Resolve Yearn vaults (Base)
  run: scripts/resolve_yearn_vaults.sh

- name: Resolve Compound/Moonwell markets (Base)
  run: scripts/resolve_compound_markets.sh

- name: Resolve ERC-4626 vaults (Base)
  run: scripts/resolve_erc4626_vaults.sh
```

Gli indirizzi risolti vengono:
1. **Esportati** per la run corrente (`$GITHUB_ENV`)
2. **Persistiti** come GitHub Environment Variables per run future

## Validazione Adapter

Per verificare la configurazione degli adapter:

```bash
cd bots/wave_rotation
python validate_adapters.py
```

**Output esempio:**
```
📊 ADAPTER SUMMARY BY TYPE:
  AAVE_V3: 4 pools
  COMET: 2 pools
  CTOKEN: 3 pools
  ERC4626: 5 pools
  LP_BEEFY_AERO: 5 pools
  YEARN: 2 pools

📋 VALIDATION RESULTS:
  Total pools configured: 21
  ✅ Valid (all env vars set): 15
  ⚠️  Invalid (missing env vars): 6
```

## Copertura del Mercato

### Protocolli Supportati
1. ✅ **Aave V3** - Lending decentralizzato
2. ✅ **Morpho Blue** - Lending ottimizzato
3. ✅ **Compound V3 (Comet)** - Lending algoritmico
4. ✅ **Moonwell** - Lending fork Compound V2
5. ✅ **Sonne Finance** - Lending su Optimism
6. ✅ **Yearn Finance** - Yield aggregation
7. ✅ **Beefy Finance** - Auto-compounding vaults
8. ✅ **ERC-4626 Vaults** - Standard vaults

### Asset Supportati su Base
- ✅ WETH (Wrapped Ethereum)
- ✅ USDC (USD Coin)
- ✅ USDbC (USD Base Coin - legacy)
- ✅ USDT (Tether)
- ✅ cbBTC (Coinbase Wrapped BTC)
- ✅ cbETH (Coinbase Wrapped ETH)
- ✅ wstETH (Wrapped Staked ETH)

### Tipologie di Strategie
1. **Single-sided lending** - Deposito singolo asset (Aave, Compound, Moonwell)
2. **Vault strategies** - Strategie ottimizzate (Yearn, Morpho)
3. **Auto-compounding** - Reinvestimento automatico (Beefy)
4. **LP farming** - Liquidity provision (Beefy + Aerodrome)

## Ordine di Probe degli Adapter Automatici

Il sistema prova gli adapter in questo ordine (vedi `auto_registry.py`):

1. **ERC4626** - Standard più generico
2. **MORPHO** - Morpho Blue vaults
3. **BEEFY** - Beefy vaults
4. **YEARN** - Yearn vaults
5. **COMET** - Compound V3
6. **CTOKEN** - Compound V2 / Moonwell
7. **SONNE** - Sonne Finance
8. **AAVEV3** - Aave V3 (richiede config pool address)

Il primo adapter che risponde positivamente al probe viene utilizzato.

## Configurazione Ambiente

### Variabili Richieste

**Token Addresses (Base - chain 8453):**
```bash
WETH_TOKEN_ADDRESS=0x4200000000000000000000000000000000000006
USDC_BASE=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
USDBC_BASE=0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA
USDT_BASE=0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2
CBBTC_BASE=0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf
CBETH_BASE=0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22
WSTETH_BASE=0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452
```

**Protocol Addresses:**
```bash
AAVE_POOL_ADDRESS_8453=0xA238Dd80C259a72e81d7e4664a9801593F98d1c5
AERODROME_ROUTER_8453=0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43
```

**Vault Addresses (popolati da script o manualmente):**
```bash
# Beefy
BEEFY_USDC_CBBTC_VAULT=
BEEFY_USDC_USDT_VAULT=
BEEFY_WETH_USDC_VAULT=
BEEFY_CBETH_WETH_VAULT=
BEEFY_WETH_USDT_VAULT=

# Yearn
YEARN_USDC_VAULT_BASE=
YEARN_WETH_VAULT_BASE=

# ERC-4626
WETH_YIELD_VAULT_BASE=0x38989BBA00BDF8181F4082995b3DEAe96163aC5D
USDC_ERC4626_VAULT=0xef417a2512C5a41f69AE4e021648b69a7CdE5D03

# Morpho
MORPHO_USDC_VAULT_BASE=0xef417a2512C5a41f69AE4e021648b69a7CdE5D03
MORPHO_WETH_VAULT_BASE=0x38989BBA00BDF8181F4082995b3DEAe96163aC5D

# Compound V3
COMET_USDC_MARKET_BASE=0x46e6b214b524310239732D51387075E0e70970bf
COMET_USDBC_MARKET_BASE=0x9c4ec768c28520B50860ea7a15bd7213a9fF58bf

# Moonwell
MOONWELL_CBETH_CTOKEN=0x3bf93770f2d4a794c3d9EBEfBAeBAE2a8f09A5E5
MOONWELL_WETH_CTOKEN=0x628ff693426583D9a7FB391E54366292F509D457
MOONWELL_USDC_CTOKEN=0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22
```

## Best Practices

1. **Esegui gli script di risoluzione** prima di ogni strategia run
2. **Valida la configurazione** con `validate_adapters.py`
3. **Usa adapter automatici** quando possibile per ridurre la configurazione manuale
4. **Testa su testnet** prima di deployment in produzione
5. **Monitora i gas costs** per operazioni cross-protocol

## Troubleshooting

### Errore: "no_assets"
**Causa:** Nessun balance dell'asset nel wallet.
**Soluzione:** Assicurati che il wallet abbia fondi sufficienti.

### Errore: "none" adapter type
**Causa:** Nessun adapter automatico ha fatto match con l'indirizzo.
**Soluzione:** Aggiungi un adapter esplicito in `config.json`.

### Errore: Missing environment variable
**Causa:** Variabile d'ambiente non impostata.
**Soluzione:** Esegui gli script di risoluzione o imposta manualmente in `.env`.

## Roadmap Futuri Adapter

Protocolli candidati per espansione futura:
- [ ] Uniswap V3 Concentrated Liquidity
- [ ] Curve Finance Stable Pools
- [ ] Convex Finance Boosted Rewards
- [ ] Pendle Finance Yield Trading
- [ ] Frax Finance Lending
- [ ] Euler Finance Lending

## Contatti & Supporto

Per problemi o domande sugli adapter:
- Consulta la documentazione in `CODEX_RULES.md`
- Verifica `IMPLEMENTATION_SUMMARY.md`
- Apri un issue su GitHub con tag `adapter`
