# Address Verification Guide

This guide explains how to populate and verify the addresses in `.env.example` for the Attuario Wallet system.

## Quick Start

The `.env.example` file now includes:
- ✅ **Pre-verified protocol addresses** (routers, NFT managers, vaults)
- ✅ **Working RPC endpoints** for all supported chains
- ✅ **Inline verification commands** for all placeholder addresses
- ✅ **Security best practices** documentation

**To use:**
1. Copy `.env.example` to `.env`: `cp .env.example .env`
2. Fill in any missing addresses you need using the instructions in this guide
3. Add your private keys and API keys (NEVER commit these!)
4. Verify addresses before using in production

## Table of Contents

1. [Overview](#overview)
2. [Security Best Practices](#security-best-practices)
3. [Verification Tools](#verification-tools)
4. [How to Find Addresses](#how-to-find-addresses)
5. [How to Verify Addresses](#how-to-verify-addresses)
6. [Chain-Specific Instructions](#chain-specific-instructions)

## Overview

The `.env.example` file contains placeholders and verified public addresses for various DeFi protocols across multiple chains. Before using any address in production, it's critical to verify it on-chain to ensure:

- The address corresponds to the correct contract
- The contract has the expected interface (token, LP, vault, etc.)
- The contract is deployed on the correct chain

## Security Best Practices

⚠️ **IMPORTANT SECURITY RULES:**

1. **NEVER commit private keys or API keys with real values to the repository**
2. **Keep sensitive credentials in your local `.env` file only** (which is gitignored)
3. **Use GitHub Secrets for CI/CD API keys and RPC endpoints**
4. **Always verify addresses from official sources before using them**
5. **Double-check chain ID when verifying addresses**

## Verification Tools

### Foundry Cast (Recommended)

Foundry's `cast` tool is the most reliable way to verify addresses on EVM chains.

**Installation:**
```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

**Basic Usage:**
```bash
# Verify a token
cast call <TOKEN_ADDRESS> "symbol()(string)" --rpc-url <RPC_URL>
cast call <TOKEN_ADDRESS> "decimals()(uint8)" --rpc-url <RPC_URL>
cast call <TOKEN_ADDRESS> "name()(string)" --rpc-url <RPC_URL>

# Verify an LP token
cast call <LP_ADDRESS> "token0()(address)" --rpc-url <RPC_URL>
cast call <LP_ADDRESS> "token1()(address)" --rpc-url <RPC_URL>

# Verify a vault
cast call <VAULT_ADDRESS> "asset()(address)" --rpc-url <RPC_URL>  # ERC-4626
cast call <VAULT_ADDRESS> "want()(address)" --rpc-url <RPC_URL>   # Beefy
```

### Automated Verification Script

We provide a helper script that automates address verification:

```bash
# Usage
./scripts/verify_addresses.sh <ADDRESS> <TYPE> [RPC_URL]

# Examples
./scripts/verify_addresses.sh 0x4200000000000000000000000000000000000006 token $BASE_RPC
./scripts/verify_addresses.sh 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5 vault $BASE_RPC
```

Supported types: `token`, `lp`, `vault`, `router`, `pool`

### Block Explorers

Always cross-reference addresses with official block explorers:

- **Base:** https://basescan.org
- **Ethereum:** https://etherscan.io
- **BSC:** https://bscscan.com
- **Arbitrum:** https://arbiscan.io
- **Avalanche:** https://snowtrace.io
- **Linea:** https://lineascan.build
- **Sonic:** https://sonicscan.org
- **Solana:** https://solscan.io
- **Aptos:** https://explorer.aptoslabs.com

## How to Find Addresses

### Protocol Documentation

The most reliable source is official protocol documentation:

- **Uniswap V2/V3:** https://docs.uniswap.org/contracts/
- **Aerodrome:** https://aerodrome.finance/
- **Balancer:** https://docs.balancer.fi/
- **Beefy:** https://app.beefy.com/ (use "Info" on vault pages)
- **Morpho:** https://docs.morpho.org/
- **Yearn:** https://docs.yearn.fi/

### DEX Interfaces

For LP tokens and pools:

1. Go to the DEX interface (Uniswap, Aerodrome, etc.)
2. Navigate to the specific pool
3. Look for "Pool Info" or "Contract Address"
4. Copy the address and verify on block explorer

### Token Lists

For standard tokens:

1. Search on CoinGecko or CoinMarketCap
2. Look for the token contract on the specific chain
3. Verify on block explorer
4. Cross-reference with the project's official documentation

### DeFi Analytics

Use analytics platforms:

- **DefiLlama:** https://defillama.com/ (TVL, protocol info)
- **GeckoTerminal:** https://www.geckoterminal.com/ (DEX pools)
- **DexScreener:** https://dexscreener.com/ (token pairs)

## How to Verify Addresses

### Step-by-Step Verification Process

#### 1. Find the Address
- Use protocol documentation or DEX interface
- Note the chain ID where the contract is deployed

#### 2. Check on Block Explorer
```
1. Go to the appropriate block explorer
2. Search for the address
3. Verify:
   - Contract is verified (green checkmark)
   - Contract name matches expected protocol
   - Contract has recent activity
```

#### 3. Verify On-Chain with Cast

**For ERC-20 Tokens:**
```bash
export BASE_RPC="https://mainnet.base.org"
export TOKEN_ADDRESS="0x4200000000000000000000000000000000000006"

# Verify symbol
cast call $TOKEN_ADDRESS "symbol()(string)" --rpc-url $BASE_RPC
# Expected: WETH or similar

# Verify decimals
cast call $TOKEN_ADDRESS "decimals()(uint8)" --rpc-url $BASE_RPC
# Expected: 18 for most tokens

# Verify name
cast call $TOKEN_ADDRESS "name()(string)" --rpc-url $BASE_RPC
```

**For LP Tokens:**
```bash
export LP_ADDRESS="0x..."

# Verify token0
cast call $LP_ADDRESS "token0()(address)" --rpc-url $BASE_RPC

# Verify token1
cast call $LP_ADDRESS "token1()(address)" --rpc-url $BASE_RPC

# Verify it's a valid pair
cast call $LP_ADDRESS "getReserves()(uint112,uint112,uint32)" --rpc-url $BASE_RPC
```

**For Vaults (ERC-4626):**
```bash
export VAULT_ADDRESS="0x..."

# Verify underlying asset
cast call $VAULT_ADDRESS "asset()(address)" --rpc-url $BASE_RPC

# Verify total assets
cast call $VAULT_ADDRESS "totalAssets()(uint256)" --rpc-url $BASE_RPC
```

**For Beefy Vaults:**
```bash
export VAULT_ADDRESS="0x..."

# Verify want token
cast call $VAULT_ADDRESS "want()(address)" --rpc-url $BASE_RPC

# Verify balance
cast call $VAULT_ADDRESS "balance()(uint256)" --rpc-url $BASE_RPC
```

#### 4. Use the Automated Script

```bash
# Verify a token
./scripts/verify_addresses.sh 0x4200000000000000000000000000000000000006 token $BASE_RPC

# Verify an LP token
./scripts/verify_addresses.sh 0x... lp $BASE_RPC

# Verify a vault
./scripts/verify_addresses.sh 0x... vault $BASE_RPC
```

## Chain-Specific Instructions

### Base Chain

**RPC Endpoint:**
```bash
BASE_RPC=https://mainnet.base.org
```

**Key Addresses Already Verified:**
- Uniswap V2 Router: `0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24`
- Uniswap V3 NFT Manager: `0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1`
- Aerodrome Slipstream NFT Manager: `0x5e7BB104d84c7CB9B682AaC2F3d509f5F406809A`
- Balancer V3 Vault: `0xbA1333333333a1BA1108E8412f11850A5C319bA9`

**Finding New Addresses:**
1. Check https://docs.base.org/base-chain/network-information/ecosystem-contracts
2. Visit protocol websites (Aerodrome, Beefy, etc.)
3. Search on https://basescan.org

### Ethereum Mainnet

**RPC Endpoint:**
```bash
ETHEREUM_RPC=https://eth.llamarpc.com
```

**Key Addresses Already Verified:**
- Uniswap V2 Router: `0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D`
- WETH: `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2`

### BSC (Binance Smart Chain)

**RPC Endpoint:**
```bash
BSC_RPC=https://bsc-dataseed.binance.org/
```

**Key Addresses Already Verified:**
- USDT (BEP-20): `0x55d398326f99059fF775485246999027B3197955`

### Sonic

**RPC Endpoint:**
```bash
SONIC_RPC=https://rpc.soniclabs.com
```

**Chain ID:** 146

**Resources:**
- Explorer: https://sonicscan.org
- Docs: https://docs.soniclabs.com

### Arbitrum

**RPC Endpoint:**
```bash
ARBITRUM_RPC=https://arb1.arbitrum.io/rpc
```

**Key Addresses Already Verified:**
- WETH: `0x82aF49447D8a07e3bd95BD0d56f35241523fBab1`

### Avalanche

**RPC Endpoint:**
```bash
AVALANCHE_RPC=https://api.avax.network/ext/bc/C/rpc
```

**Key Addresses Already Verified:**
- WETH.e: `0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB`

### Linea

**RPC Endpoint:**
```bash
LINEA_RPC=https://rpc.linea.build
```

**Key Addresses Already Verified:**
- WETH: `0xe5D7C2a44FfDDf6b295A15c148167daaAf5Cf34f`

### Solana

**RPC Endpoint:**
```bash
SOLANA_RPC=https://api.mainnet-beta.solana.com
```

**Verification (requires Solana CLI):**
```bash
solana account <ADDRESS> --url $SOLANA_RPC
```

**Key Addresses Already Verified:**
- Raydium AMM Program: `675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8`
- USDC: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`
- WSOL: `So11111111111111111111111111111111111111112`

**Note:** Solana requires different tools (solana-py SDK) and has a different address format.

### Aptos

**RPC Endpoint:**
```bash
APTOS_RPC=https://fullnode.mainnet.aptoslabs.com/v1
```

**Verification (requires Aptos CLI):**
```bash
aptos account list --account <ADDRESS> --url $APTOS_RPC
```

**Key Addresses Already Verified:**
- APT Token: `0x1::aptos_coin::AptosCoin`

**Note:** Aptos requires aptos-sdk and has a different address format (module paths).

## Common Verification Errors

### "reverted" or "execution reverted"
- The contract doesn't implement the function you're calling
- Wrong contract type (e.g., calling token functions on a vault)
- Contract may be paused or have access controls

### "could not decode output"
- Function signature is correct but return type doesn't match
- Try with different function signatures

### "timeout" or "connection refused"
- RPC endpoint is down or rate-limited
- Try a different RPC endpoint

### Wrong Values Returned
- You may be on the wrong chain
- Check chain ID: `cast chain-id --rpc-url $RPC_URL`
- Verify the address on the block explorer for that chain

## Next Steps

1. **Fill in missing addresses** using the methods above
2. **Verify each address** before adding to your local `.env`
3. **Test with small amounts** before deploying to production
4. **Run the validation script** to check coverage:
   ```bash
   python bots/wave_rotation/validate_50_assets.py
   ```

## Contributing

When adding new addresses to `.env.example`:

1. Always include a comment with the verification source
2. Add instructions on how to verify the address
3. Never commit real private keys or API keys
4. Keep the format consistent with existing entries

## Support

For issues or questions:
- Check the official documentation for each protocol
- Search on block explorers
- Use the community Discord/Telegram channels
- Create an issue in the repository

---

**Remember:** Always verify addresses from multiple sources before using them in production!
