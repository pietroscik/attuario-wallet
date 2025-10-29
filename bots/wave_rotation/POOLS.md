# Pool Configurations

This document describes all the pool configurations available in the Attuario Wave Rotation strategy.

## Pool Categories

### 1. Lending Pools (Aave v3)

These pools use the Aave v3 protocol for lending and borrowing.

#### `pool:base:aave-v3:WETH`
- **Type**: Aave v3 Lending
- **Asset**: WETH (Wrapped ETH)
- **Description**: Supply WETH to Aave v3 to earn lending yield
- **Decimals**: 18

#### `pool:base:aave-v3:USDC`
- **Type**: Aave v3 Lending
- **Asset**: USDC
- **Description**: Supply USDC to Aave v3 to earn lending yield
- **Decimals**: 6

#### `pool:base:aave-v3:cbBTC`
- **Type**: Aave v3 Lending
- **Asset**: cbBTC (Coinbase Wrapped BTC)
- **Description**: Supply cbBTC to Aave v3 to earn lending yield on Bitcoin
- **Decimals**: 8

#### `pool:base:aave-v3:cbETH`
- **Type**: Aave v3 Lending
- **Asset**: cbETH (Coinbase Wrapped staked ETH)
- **Description**: Supply cbETH to Aave v3 to earn lending yield
- **Decimals**: 18

### 2. Liquidity Pool Pairs (Beefy + Aerodrome)

These pools provide liquidity on Aerodrome DEX and stake the LP tokens in Beefy vaults for additional yield.

#### `pool:base:beefy:USDC-cbBTC`
- **Type**: Beefy/Aerodrome LP
- **Pair**: USDC/cbBTC
- **Description**: Volatile pool pairing stablecoin with Bitcoin exposure
- **Slippage**: 50 bps

#### `pool:base:beefy:USDC-USDT` (Stable/Stable)
- **Type**: Beefy/Aerodrome LP
- **Pair**: USDC/USDT
- **Description**: Stable pool between two major stablecoins
- **Stable**: true (uses Curve-style stable swap math)
- **Slippage**: 30 bps (lower due to stable correlation)

#### `pool:base:beefy:WETH-USDC` (ETH/Stable)
- **Type**: Beefy/Aerodrome LP
- **Pair**: WETH/USDC
- **Description**: Main ETH/stablecoin pair with high liquidity
- **Slippage**: 50 bps

#### `pool:base:beefy:cbETH-WETH` (LST Pool)
- **Type**: Beefy/Aerodrome LP
- **Pair**: cbETH/WETH
- **Description**: Liquid Staking Token pool pairing Coinbase staked ETH with regular ETH
- **Slippage**: 50 bps

#### `pool:base:beefy:WETH-USDT` (ETH/Stable)
- **Type**: Beefy/Aerodrome LP
- **Pair**: WETH/USDT
- **Description**: Alternative ETH/stablecoin pair using USDT
- **Slippage**: 50 bps

### 3. ERC-4626 Vaults

These pools use the ERC-4626 vault standard for various yield strategies.

#### `pool:base:erc4626:WETH-yield`
- **Type**: ERC-4626 Vault
- **Asset**: WETH
- **Description**: Yield-bearing vault per accumulare rendimento su WETH tramite Morpho × Yearn

#### `pool:base:erc4626:cbBTC-vault`
- **Type**: ERC-4626 Vault
- **Asset**: cbBTC
- **Description**: Vault strategy for cbBTC yield generation

#### `pool:base:erc4626:USDC-vault`
- **Type**: ERC-4626 Vault
- **Asset**: USDC
- **Description**: Vault strategy for USDC yield generation

#### `pool:base:morpho:USDC`
- **Type**: ERC-4626 Vault (Morpho Blue)
- **Asset**: USDC
- **Description**: Deposito Morpho Blue su USDC con interfaccia ERC-4626

#### `pool:base:morpho:WETH`
- **Type**: ERC-4626 Vault (Morpho Blue)
- **Asset**: WETH
- **Description**: Deposito Morpho Blue su WETH con interfaccia ERC-4626

### 4. Yearn Vaults

Yearn-style vaults that expose a deposit/withdraw interface similar to ERC20 tokens.

#### `pool:base:yearn:USDC`
- **Type**: Yearn Vault
- **Asset**: USDC
- **Description**: Deposita USDC in un vault Yearn su Base per rendimento attivo

#### `pool:base:yearn:WETH`
- **Type**: Yearn Vault
- **Asset**: WETH
- **Description**: Deposita WETH nel vault Yearn dedicato su Base

### 5. Additional Lending Markets (Compound / Moonwell)

Markets basati su Compound v3 (Comet) e cTokens stile Compound v2.

#### `pool:base:comet:USDC`
- **Type**: Compound v3 (Comet)
- **Asset**: USDC
- **Description**: Fornisce USDC al mercato Comet per ottenere rendimento e ricompense

#### `pool:base:comet:USDbC`
- **Type**: Compound v3 (Comet)
- **Asset**: USDbC
- **Description**: Supporta il mercato Comet per USDbC (stablecoin legacy su Base)

#### `pool:base:moonwell:cbETH`
- **Type**: Moonwell / Compound v2 cToken
- **Asset**: cbETH
- **Description**: Deposita cbETH nel mercato Moonwell per accumulare interessi a tasso variabile

#### `pool:base:moonwell:WETH`
- **Type**: Moonwell / Compound v2 cToken
- **Asset**: WETH
- **Description**: Deposita WETH nel mercato Moonwell per accumulare interessi e reward

#### `pool:base:moonwell:USDC`
- **Type**: Moonwell / Compound v2 cToken
- **Asset**: USDC
- **Description**: Deposita USDC nel mercato Moonwell per rendimento su stablecoin

## Configuration Requirements

Each pool requires specific environment variables to be set:

### Token Addresses
- `WETH_TOKEN_ADDRESS`: Native WETH on Base
- `USDC_BASE`: Native USDC on Base
- `USDBC_BASE`: Bridged USDbC on Base
- `USDT_BASE`: USDT on Base
- `CBBTC_BASE`: Coinbase Wrapped BTC on Base
- `CBETH_BASE`: Coinbase Wrapped staked ETH on Base
- `WSTETH_BASE`: Wrapped staked ETH on Base

### Protocol Addresses
- `AAVE_POOL_ADDRESS_8453`: Aave v3 Pool contract on Base
- `AAVE_WETH_GATEWAY_8453`: WETH Gateway (optional, solo per depositi nativi)
- `AERODROME_ROUTER_8453`: Aerodrome Router contract on Base

### Vault & Market Addresses
Queste variabili vengono risolte dagli script di supporto oppure possono essere impostate manualmente:
- `BEEFY_USDC_CBBTC_VAULT`
- `BEEFY_USDC_USDT_VAULT`
- `BEEFY_WETH_USDC_VAULT`
- `BEEFY_CBETH_WETH_VAULT`
- `BEEFY_WETH_USDT_VAULT`
- `WETH_YIELD_VAULT_BASE`
- `CBBTC_ERC4626_VAULT`
- `USDC_ERC4626_VAULT`
- `MORPHO_USDC_VAULT_BASE`
- `MORPHO_WETH_VAULT_BASE`
- `YEARN_USDC_VAULT_BASE`
- `YEARN_WETH_VAULT_BASE`
- `COMET_USDC_MARKET_BASE`
- `COMET_USDBC_MARKET_BASE`
- `MOONWELL_CBETH_CTOKEN`
- `MOONWELL_WETH_CTOKEN`
- `MOONWELL_USDC_CTOKEN`

## Pool Selection Strategy

The Wave Rotation strategy evaluates all configured pools based on:

1. **APY**: Annual Percentage Yield
2. **TVL**: Total Value Locked (minimum $100,000)
3. **Risk Score**: Protocol risk assessment (0-1, default 0)
4. **Fees**: Operational costs (gas, slippage, protocol fees)

The score formula is:
```
Score = r_daily / (1 + cost_pct * (1 - risk_score))
```

Where:
- `r_daily = (1 + APY)^(1/365) - 1`
- `cost_pct` = estimated operational costs
- `risk_score` = protocol risk proxy

## Pool Categories Summary

| Category | Count | Purpose |
|----------|-------|---------|
| Lending (Aave v3) | 4 | Stable lending yield on various assets |
| LP Pairs (Beefy/Aero) | 5 | Liquidity provision + farming rewards |
| ERC-4626 & Morpho Vaults | 5 | Vault strategies e Morpho Blue |
| Yearn Vaults | 2 | Yield vault con strategia attiva su USDC e WETH |
| Compound v3 (Comet) | 2 | Lending single-sided con collateral isolato |
| Compound v2 (Moonwell) | 3 | Lending tradizionale con cToken |
| **Total** | **21** | Copertura DeFi multi-protocollo |

## Adapter Types

- **aave_v3**: Single-sided lending on Aave v3
- **lp_beefy_aero**: Dual-sided LP provision on Aerodrome with Beefy farming
- **erc4626**: Standard ERC-4626 vault deposits
- **yearn**: Vault Yearn con interfaccia ERC20
- **comet**: Mercati Compound v3 (Comet) single-asset
- **ctoken**: Mercati Compound v2/Moonwell basati su cToken

## Notes

1. All pools on Base chain (Chain ID: 8453)
2. Environment variables must be set with actual addresses before execution
3. The strategy automatically selects the best-scoring pool based on real-time data
4. Capital switches only when new pool score exceeds current by ≥1% (delta_switch)
5. 50% of profits reinvested, 50% sent to treasury (USDC)
