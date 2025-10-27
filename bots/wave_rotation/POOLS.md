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

#### `pool:base:erc4626:stETH-yield`
- **Type**: ERC-4626 Vault
- **Asset**: wstETH (Wrapped staked ETH)
- **Description**: Yield-bearing vault for stETH staking rewards

#### `pool:base:erc4626:cbBTC-vault`
- **Type**: ERC-4626 Vault
- **Asset**: cbBTC
- **Description**: Vault strategy for cbBTC yield generation

#### `pool:base:erc4626:USDC-vault`
- **Type**: ERC-4626 Vault
- **Asset**: USDC
- **Description**: Vault strategy for USDC yield generation

## Configuration Requirements

Each pool requires specific environment variables to be set:

### Token Addresses
- `WETH_TOKEN_ADDRESS`: Native WETH on Base
- `USDC_BASE`: Native USDC on Base
- `USDT_BASE`: USDT on Base
- `CBBTC_BASE`: Coinbase Wrapped BTC on Base
- `CBETH_BASE`: Coinbase Wrapped staked ETH on Base
- `WSTETH_BASE`: Wrapped staked ETH on Base

### Protocol Addresses
- `AAVE_POOL_ADDRESS_8453`: Aave v3 Pool contract on Base
- `AERODROME_ROUTER_8453`: Aerodrome Router contract on Base

### Vault Addresses
Each Beefy and ERC-4626 pool requires its specific vault address:
- `BEEFY_USDC_CBBTC_VAULT`
- `BEEFY_USDC_USDT_VAULT`
- `BEEFY_WETH_USDC_VAULT`
- `BEEFY_CBETH_WETH_VAULT`
- `BEEFY_WETH_USDT_VAULT`
- `STETH_YIELD_VAULT_BASE`
- `CBBTC_ERC4626_VAULT`
- `USDC_ERC4626_VAULT`

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
| ERC-4626 Vaults | 3 | Specialized yield strategies |
| **Total** | **12** | Comprehensive coverage across DeFi sectors |

## Adapter Types

- **aave_v3**: Single-sided lending on Aave v3
- **lp_beefy_aero**: Dual-sided LP provision on Aerodrome with Beefy farming
- **erc4626**: Standard ERC-4626 vault deposits

## Notes

1. All pools on Base chain (Chain ID: 8453)
2. Environment variables must be set with actual addresses before execution
3. The strategy automatically selects the best-scoring pool based on real-time data
4. Capital switches only when new pool score exceeds current by ≥1% (delta_switch)
5. 50% of profits reinvested, 50% sent to treasury (USDC)
