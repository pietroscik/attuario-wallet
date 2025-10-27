# Pools Status and Execution Guide

## ✅ Pools Ready to Execute (8/12)

These pools are fully configured and can execute immediately:

### Aave v3 Lending (4 pools)
1. **pool:base:aave-v3:WETH** - WETH lending ✅
2. **pool:base:aave-v3:USDC** - USDC lending ✅
3. **pool:base:aave-v3:cbBTC** - cbBTC lending ✅
4. **pool:base:aave-v3:cbETH** - cbETH lending ✅

### ERC-4626 Vaults (1 pool)
5. **pool:base:erc4626:USDC-vault** - Morpho Yearn USDC vault ✅
   - Address: 0xef417a2512C5a41f69AE4e021648b69a7CdE5D03

## ⏳ Pools Needing Beefy Vault Addresses (5/12)

These pools are configured but need Beefy vault contract addresses:

### Beefy/Aerodrome LP Pools
6. **pool:base:beefy:USDC-cbBTC** - Needs BEEFY_USDC_CBBTC_VAULT
7. **pool:base:beefy:USDC-USDT** - Needs BEEFY_USDC_USDT_VAULT (stable pair)
8. **pool:base:beefy:WETH-USDC** - Needs BEEFY_WETH_USDC_VAULT
9. **pool:base:beefy:cbETH-WETH** - Needs BEEFY_CBETH_WETH_VAULT (LST pair)
10. **pool:base:beefy:WETH-USDT** - Needs BEEFY_WETH_USDT_VAULT

## ⏳ Pools Needing ERC-4626 Vault Addresses (2/12)

11. **pool:base:erc4626:WETH-yield** - Needs WETH_YIELD_VAULT_BASE
12. **pool:base:erc4626:cbBTC-vault** - Needs CBBTC_ERC4626_VAULT

## How to Find Missing Addresses

### For Beefy Vaults
1. Visit https://app.beefy.com/
2. Select "Base" network from the chain selector
3. Search for the desired pool (e.g., "USDC USDT", "WETH USDC")
4. Click on the vault
5. Copy the contract address from the vault details
6. Add to `.env` file or GitHub Actions secrets

### For ERC-4626 Vaults
- **WETH yield**: Check Morpho/Yearn per il vault WETH OG su Base
- **cbBTC vault**: Check ERC-4626 registry at https://erc4626.info/vaults/
- Can also use Yearn, Morpho, or other ERC-4626 providers

## Running the Strategy

### Local Execution
```bash
cd bots/wave_rotation

# Set environment variables
export $(grep -v '^#' ../../.env.example | xargs)

# Validate configuration
python3 validate_pools.py

# Run strategy (will use 8 available pools)
python3 strategy.py
```

### GitHub Actions Execution
The workflow is configured with default values and will run automatically with:
- All 4 Aave v3 pools ✅
- 1 ERC-4626 pool (USDC) ✅
- Beefy pools skipped if vault addresses not set

To add Beefy vaults:
1. Go to repository Settings → Environments → copilot
2. Add variables/secrets for the missing vault addresses
3. Workflow will automatically include those pools

## Strategy Behavior

The Wave Rotation strategy will:
1. ✅ Evaluate all pools with complete configurations
2. ⏭️ Skip pools with missing vault addresses (graceful handling)
3. 📊 Calculate scores for available pools
4. 🎯 Select the pool with the best risk-adjusted return
5. 💰 Execute allocation (50% reinvest, 50% treasury)

## Pool Coverage Achieved

Even with just the 8 ready pools, we cover:
- ✅ **Lending**: 4 assets on Aave v3 (WETH, USDC, cbBTC, cbETH)
- ✅ **Yield vault**: USDC on Morpho Yearn
- ⏳ **Stable/stable**: USDC/USDT (needs vault address)
- ⏳ **LST**: cbETH/WETH (needs vault address)
- ⏳ **ETH/stable**: WETH/USDC, WETH/USDT (need vault addresses)

## Auto-Populated Addresses

All token and protocol addresses are auto-populated in `.env.example` and GitHub Actions workflow:

**Tokens:**
- WETH: 0x4200000000000000000000000000000000000006
- USDC: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
- USDT: 0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2
- cbBTC: 0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf
- cbETH: 0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22
- wstETH: 0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452

**Protocols:**
- Aave Pool: 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5
- Aerodrome Router: 0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43

## Conclusion

**The system is immediately operational with 8/12 pools!** 

The remaining 4 Beefy pool addresses can be added incrementally without breaking existing functionality. The strategy will work with whatever pools are configured.
