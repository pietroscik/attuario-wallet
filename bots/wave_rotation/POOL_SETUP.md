# Adding and Configuring Additional Pools

This guide explains how to configure and use the newly added pool configurations in the Attuario Wave Rotation strategy.

## Overview

The Wave Rotation strategy now supports 12 pools across 3 major DeFi categories:
- **4 Aave v3 Lending Pools**: WETH, USDC, cbBTC, cbETH
- **5 Beefy/Aerodrome LP Pools**: USDC/cbBTC, USDC/USDT, WETH/USDC, cbETH/WETH, WETH/USDT
- **3 ERC-4626 Vaults**: WETH yield, cbBTC vault, USDC vault

## Quick Start

### 1. Check Current Configuration

Run the validation script to see which pools are ready:

```bash
cd bots/wave_rotation
python3 validate_pools.py
```

This will show you which environment variables are missing.

### 2. Set Environment Variables

Copy `.env.example` to `.env` and fill in the required addresses:

```bash
cp .env.example .env
# Edit .env with your preferred editor
```

#### Required Token Addresses (Base Chain - ID: 8453)

These are already set in `.env.example`:
```bash
WETH_TOKEN_ADDRESS=0x4200000000000000000000000000000000000006
USDC_BASE=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
CBBTC_BASE=0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf
AAVE_POOL_ADDRESS_8453=0xA238Dd80C259a72e81d7e4664a9801593F98d1c5
AERODROME_ROUTER_8453=0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43
```

#### Additional Token Addresses to Set

```bash
# You need to find and set these:
USDT_BASE=          # USDT token address on Base
CBETH_BASE=         # Coinbase ETH token address on Base
WSTETH_BASE=        # Wrapped staked ETH address on Base (if available)
```

#### Vault Addresses to Set

You need to research and set the actual vault addresses on Base:

```bash
# Beefy Vaults (find on Beefy Finance)
BEEFY_USDC_USDT_VAULT=
BEEFY_WETH_USDC_VAULT=
BEEFY_CBETH_WETH_VAULT=
BEEFY_WETH_USDT_VAULT=

# ERC-4626 Vaults (depends on your chosen protocols)
WETH_YIELD_VAULT_BASE=
CBBTC_ERC4626_VAULT=
USDC_ERC4626_VAULT=
```

### 3. Find Vault Addresses

#### For Beefy Vaults:
1. Visit https://app.beefy.com/
2. Select "Base" network
3. Search for the desired pool (e.g., "USDC-USDT" or "ETH-USDC")
4. Click on the vault and copy its contract address
5. Add it to your `.env` file

#### For ERC-4626 Vaults:
1. Identify which ERC-4626 compliant vaults are available on Base
2. Popular options include:
   - Yearn Finance vaults
   - Morpho vaults
   - Custom protocol vaults
3. Get the vault contract address from their respective platforms

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

### ERC-4626 Vaults

Standard vault interface for various yield strategies:
- `pool:base:erc4626:WETH-yield` - **WETH yield** via Morpho × Yearn vault
- `pool:base:erc4626:cbBTC-vault` - Bitcoin yield strategies
- `pool:base:erc4626:USDC-vault` - Stablecoin yield strategies

**Advantages**: Professional strategy management, single token deposit
**Disadvantages**: Strategy-dependent risk

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
   - `erc4626` - for ERC-4626 compatible vaults

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
