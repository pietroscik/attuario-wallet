# Adding and Configuring Additional Pools

This guide explains how to configure and use the newly added pool configurations in the Attuario Wave Rotation strategy.

## Overview

The Wave Rotation strategy now supports 21 pools across 6 major DeFi categories:
- **4 Aave v3 Lending Pools**: WETH, USDC, cbBTC, cbETH
- **5 Beefy/Aerodrome LP Pools**: USDC/cbBTC, USDC/USDT, WETH/USDC, cbETH/WETH, WETH/USDT
- **5 ERC-4626 & Morpho Vaults**: WETH yield, cbBTC vault, USDC vault, Morpho USDC, Morpho WETH
- **2 Yearn Vaults**: Yearn USDC e Yearn WETH su Base
- **2 Compound v3 (Comet) Markets**: USDC e USDbC
- **3 Moonwell cToken Markets**: cbETH, WETH, USDC

## Quick Start

### 1. Check Current Configuration

Run the validation script to see which pools are ready:

```bash
cd bots/wave_rotation
python3 validate_pools.py
```

This will show you which environment variables are missing.

### 2. Populate Environment Variables

```bash
cp .env.example .env
./scripts/resolve_beefy_vaults.sh
./scripts/resolve_yearn_vaults.sh
./scripts/resolve_compound_markets.sh
./scripts/resolve_erc4626_vaults.sh
```

The scripts fetch the latest addresses from Beefy, Yearn (yDaemon), Morpho, Compound/Moonwell APIs and write them into `.env` (and optionally in GitHub Environment Variables). If an API call fails you can edit `.env` manually and rerun the validation.

#### Token Addresses (Base Chain - ID: 8453)

Already prefilled in `.env.example`:
```bash
WETH_TOKEN_ADDRESS=0x4200000000000000000000000000000000000006
USDC_BASE=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
USDBC_BASE=0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA
USDT_BASE=0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2
CBBTC_BASE=0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf
CBETH_BASE=0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22
WSTETH_BASE=0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452
AAVE_POOL_ADDRESS_8453=0xA238Dd80C259a72e81d7e4664a9801593F98d1c5
AERODROME_ROUTER_8453=0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43
```

#### Auto-resolved Vaults & Markets

The scripts populate (or refresh) the following variables:
```bash
# Beefy vaults
BEEFY_USDC_CBBTC_VAULT=0x...
BEEFY_USDC_USDT_VAULT=0x...
BEEFY_WETH_USDC_VAULT=0x...
BEEFY_CBETH_WETH_VAULT=0x...
BEEFY_WETH_USDT_VAULT=0x...

# ERC-4626 & Morpho vaults
WETH_YIELD_VAULT_BASE=0x38989BBA00BDF8181F4082995b3DEAe96163aC5D
CBBTC_ERC4626_VAULT=0x...
USDC_ERC4626_VAULT=0xef417a2512C5a41f69AE4e021648b69a7CdE5D03
MORPHO_USDC_VAULT_BASE=0xef417a2512C5a41f69AE4e021648b69a7CdE5D03
MORPHO_WETH_VAULT_BASE=0x38989BBA00BDF8181F4082995b3DEAe96163aC5D

# Yearn vaults (via yDaemon)
YEARN_USDC_VAULT_BASE=0xef417a2512C5a41f69AE4e021648b69a7CdE5D03
YEARN_WETH_VAULT_BASE=0x38989BBA00BDF8181F4082995b3DEAe96163aC5D

# Compound / Moonwell markets
COMET_USDC_MARKET_BASE=0x46e6b214b524310239732D51387075E0e70970bf
COMET_USDBC_MARKET_BASE=0x9c4ec768c28520B50860ea7a15bd7213a9fF58bf
MOONWELL_CBETH_CTOKEN=0x3bf93770f2d4a794c3d9EBEfBAeBAE2a8f09A5E5
MOONWELL_WETH_CTOKEN=0x628ff693426583D9a7FB391E54366292F509D457
MOONWELL_USDC_CTOKEN=0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22
```

### 3. Manual Overrides (Optional)

If an API endpoint is unavailable you can still populate values manually:

- **Beefy Vaults**: visita https://app.beefy.com/ → chain “Base” → apri il vault (es. “USDC-USDT”) → copia l’indirizzo → aggiorna la variabile `BEEFY_*_VAULT`.  
- **ERC-4626/Morpho Vaults**: verifica l’indirizzo sulla dashboard del protocollo (Yearn, Morpho, ecc.) oppure sulla registry https://erc4626.info/.  
- **Comet/Moonwell Markets**: recupera gli address ufficiali dalla documentazione Chainlight, Compound o Moonwell e imposta `COMET_*` / `MOONWELL_*_CTOKEN`.

### 4. Validate Configuration

After setting the environment variables, run validation again:

```bash
python3 validate_pools.py
```

You should see all pools marked as "Ready" (✓).

### 5. Test Pool Configuration

Run the pool configuration tests:

```bash
python3 test_pools.py
```

This verifies that:
- All pool types are valid
- Required fields are present
- All categories are covered

## Pool Categories Explained

### Lending Pools (Aave v3)

Single-sided deposits that earn lending interest:
- `pool:base:aave-v3:WETH` - Lend WETH
- `pool:base:aave-v3:USDC` - Lend USDC
- `pool:base:aave-v3:cbBTC` - Lend cbBTC
- `pool:base:aave-v3:cbETH` - Lend cbETH

**Advantages**: Lower risk, no impermanent loss
**Disadvantages**: Lower yields compared to LP pools

### Liquidity Pool Pairs (Beefy + Aerodrome)

Provide liquidity on Aerodrome DEX and stake LP tokens in Beefy:
- `pool:base:beefy:USDC-USDT` - **Stable/Stable** (lowest IL risk)
- `pool:base:beefy:USDC-cbBTC` - BTC exposure with stablecoin
- `pool:base:beefy:WETH-USDC` - **ETH/Stable** (medium IL risk)
- `pool:base:beefy:WETH-USDT` - **ETH/Stable** alternative
- `pool:base:beefy:cbETH-WETH` - **LST Pool** (low IL risk, similar assets)

**Advantages**: Higher yields from trading fees + farming
**Disadvantages**: Impermanent loss risk, requires both tokens

### ERC-4626 & Morpho Vaults

Standard ERC-4626 interface utilizzata da vault Yearn/Morpho:
- `pool:base:erc4626:WETH-yield` - **WETH yield** via Morpho × Yearn vault
- `pool:base:erc4626:cbBTC-vault` - Bitcoin yield strategies
- `pool:base:erc4626:USDC-vault` - Stablecoin yield strategies
- `pool:base:morpho:USDC` - Morpho Blue USDC (ERC-4626 compliant)
- `pool:base:morpho:WETH` - Morpho Blue WETH (ERC-4626 compliant)

**Advantages**: Professional strategy management, single token deposit
**Disadvantages**: Strategy-dependent risk

### Yearn Vaults

Vault tradizionali Yearn con depositi single-sided:
- `pool:base:yearn:USDC` - Vault Yearn su Base per USDC
- `pool:base:yearn:WETH` - Vault Yearn WETH integrato via yDaemon

**Advantages**: Strategia attiva con auto-compounding
**Disadvantages**: Dipendenza dalla gestione Yearn

### Compound-based Lending (Comet & Moonwell)

Mercati lending con interfaccia Compound v3/v2:
- `pool:base:comet:USDC` - Mercato Comet per USDC
- `pool:base:comet:USDbC` - Mercato Comet per USDbC (legacy stablecoin)
- `pool:base:moonwell:cbETH` - Mercato Moonwell cToken per cbETH
- `pool:base:moonwell:WETH` - Mercato Moonwell cToken per WETH
- `pool:base:moonwell:USDC` - Mercato Moonwell cToken per USDC

**Advantages**: Ulteriore diversificazione dei protocolli di lending
**Disadvantages**: Rischi specifici dei mercati Compound (health factor, interessi variabili)

## How the Strategy Selects Pools

The Wave Rotation strategy evaluates all configured pools and selects the best one based on:

1. **Score Calculation**:
   ```
   Score = r_daily / (1 + cost_pct * (1 - risk_score))
   ```
   Where:
   - `r_daily` = daily return from APY
   - `cost_pct` = operational costs (gas, fees, slippage)
   - `risk_score` = protocol risk (0-1)

2. **Switching Rules**:
   - Only switches if new pool score is ≥1% better
   - Minimum TVL requirement: $100,000
   - Considers transaction costs

3. **Risk Management**:
   - Stop-loss: -10% daily
   - Auto-pause after 3 consecutive losses
   - 50% profit reinvestment, 50% to treasury

## Troubleshooting

### "Missing environment variable" errors

**Solution**: Check that all required variables are set in your `.env` file.

### "Unknown adapter type" errors

**Solution**: This shouldn't happen with the provided configuration. Verify your `config.json` hasn't been corrupted.

### "No module named 'web3'" errors

**Solution**: Install Python dependencies:
```bash
pip install -r requirements.txt
```

### Pool not being selected

**Possible reasons**:
1. TVL below $100,000 minimum
2. APY not competitive compared to other pools
3. High operational costs reducing the score
4. Missing or incorrect vault address

**Debug steps**:
1. Check DeFiLlama data for the pool
2. Verify vault address is correct
3. Test manually with the adapter

## Advanced: Adding Custom Pools

To add your own pool:

1. Choose the appropriate adapter type:
   - `aave_v3` - for Aave v3 lending
   - `lp_beefy_aero` - for Beefy vaults on Aerodrome LPs
   - `erc4626` - for ERC-4626 compatible vaults (incl. Morpho)
   - `yearn` - for Yearn vaults risolti via yDaemon
   - `comet` - for Compound v3 / Comet markets
   - `ctoken` - for Compound v2 style markets (Moonwell, Sonne, ecc.)

2. Add configuration to `config.json`:
   ```json
   "pool:base:custom:MyPool": {
     "type": "erc4626",
     "vault": "${MY_VAULT_ADDRESS}",
     "asset": "${MY_ASSET_ADDRESS}"
   }
   ```

3. Add environment variables to `.env`:
   ```bash
   MY_VAULT_ADDRESS=0x...
   MY_ASSET_ADDRESS=0x...
   ```

4. Validate and test:
   ```bash
   python3 validate_pools.py
   python3 test_pools.py
   ```

## Support

For detailed pool information, see `POOLS.md`.

For strategy rules and mechanics, see `CODEX_RULES.md`.

If you encounter issues:
1. Check the validation output
2. Verify all addresses are correct for Base chain
3. Ensure sufficient balance in your wallet
4. Review logs in `daily.log`
