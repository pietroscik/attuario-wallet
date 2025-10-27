# GitHub Actions Environment Configuration

This document lists all the secrets and variables that need to be configured in the GitHub Actions environment for the "Run Strategy" workflow to execute successfully with all pools.

## Setting Up Secrets

Go to your repository → Settings → Environments → copilot → Add secret

## Required Secrets

### Core Configuration
- `RPC_URL` - Base RPC endpoint (e.g., https://mainnet.base.org)
- `RPC_FALLBACKS` - Fallback RPC endpoints (comma-separated)
- `PRIVATE_KEY` - Private key for executing transactions (0x...)
- `VAULT_ADDRESS` - Address of the AttuarioVault contract
- `TELEGRAM_TOKEN` - Telegram bot token (optional)
- `TELEGRAM_CHATID` - Telegram chat ID (optional)
- `ALCHEMY_API_KEY` - Alchemy API key (optional)

### Protocol Addresses on Base (Chain ID: 8453)
- `AAVE_POOL_ADDRESS_8453` - Aave v3 Pool contract (0xA238Dd80C259a72e81d7e4664a9801593F98d1c5)
- `AAVE_WETH_GATEWAY_8453` - Aave WETH Gateway contract (optional)
- `AERODROME_ROUTER_8453` - Aerodrome Router contract (0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43)

### Token Addresses on Base
- `WETH_TOKEN_ADDRESS` - Wrapped ETH (0x4200000000000000000000000000000000000006)
- `USDC_BASE` - USDC token (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913)
- `USDBC_BASE` - Bridged USDC (0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA)
- `USDT_BASE` - USDT token (0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2)
- `CBBTC_BASE` - Coinbase Wrapped BTC (0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf)
- `CBETH_BASE` - Coinbase Wrapped staked ETH (0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22)
- `WSTETH_BASE` - Wrapped staked ETH (if available on Base)

### Beefy Vault Addresses on Base
These need to be found on https://app.beefy.com/ for Base network:

- `BEEFY_USDC_CBBTC_VAULT` - Beefy vault for USDC/cbBTC LP
- `BEEFY_USDC_USDT_VAULT` - Beefy vault for USDC/USDT stable LP
- `BEEFY_WETH_USDC_VAULT` - Beefy vault for WETH/USDC LP
- `BEEFY_CBETH_WETH_VAULT` - Beefy vault for cbETH/WETH LP
- `BEEFY_WETH_USDT_VAULT` - Beefy vault for WETH/USDT LP

### ERC-4626 Vault Addresses on Base
Questi indirizzi dipendono dai protocolli che intendi usare:

- `WETH_YIELD_VAULT_BASE` - Vault ERC-4626 per la strategia WETH (Morpho × Yearn)
- `CBBTC_ERC4626_VAULT` - Vault ERC-4626 per la strategia cbBTC
- `USDC_ERC4626_VAULT` - Vault ERC-4626 per la strategia USDC

## Finding Vault Addresses

### Beefy Vaults
1. Visit https://app.beefy.com/
2. Select "Base" network
3. Search for the desired pool (e.g., "USDC-USDT" or "ETH-USDC")
4. Click on the vault
5. Copy the contract address
6. Add it as a secret in GitHub Actions

### ERC-4626 Vaults
ERC-4626 vaults are available from various protocols:
- **Yearn Finance**: Check if they have Base vaults
- **Morpho**: Look for Morpho vaults on Base
- **Other protocols**: Research which protocols offer ERC-4626 vaults on Base

## Pools That Will Work

After setting all secrets, the following pools will be available:

### Fully Configured (with known addresses)
- `pool:base:aave-v3:WETH` - WETH lending on Aave v3
- `pool:base:aave-v3:USDC` - USDC lending on Aave v3
- `pool:base:aave-v3:cbBTC` - cbBTC lending on Aave v3

### Need Vault Addresses
- `pool:base:aave-v3:cbETH` - Needs CBETH_BASE
- `pool:base:beefy:USDC-cbBTC` - Needs BEEFY_USDC_CBBTC_VAULT
- `pool:base:beefy:USDC-USDT` - Needs BEEFY_USDC_USDT_VAULT + USDT_BASE
- `pool:base:beefy:WETH-USDC` - Needs BEEFY_WETH_USDC_VAULT
- `pool:base:beefy:cbETH-WETH` - Needs BEEFY_CBETH_WETH_VAULT + CBETH_BASE
- `pool:base:beefy:WETH-USDT` - Needs BEEFY_WETH_USDT_VAULT + USDT_BASE
- `pool:base:erc4626:WETH-yield` - Needs WETH_YIELD_VAULT_BASE
- `pool:base:erc4626:cbBTC-vault` - Needs CBBTC_ERC4626_VAULT
- `pool:base:erc4626:USDC-vault` - Needs USDC_ERC4626_VAULT

## Validation

After setting all secrets in GitHub Actions:

1. The workflow will automatically have access to all environment variables
2. Pools with missing addresses will be skipped by the strategy
3. The strategy will only select from pools with complete configurations
4. Check workflow logs to see which pools are available

## Notes

- Some secrets can be left empty if you don't want to use certain pools
- Token addresses marked with known values are included in the workflow
- All secrets should be set even if empty (GitHub Actions requirement)
- The strategy gracefully handles missing vault addresses by skipping those pools
- You can start with a subset of pools and add more vault addresses over time
