# Asset to Adapter Mapping

This document maps each of the 50 assets to their appropriate adapter type and provides the configuration template.

## Assets by Adapter Type

### uniswap_v2 (22 assets on Base, 1 on Ethereum)

**Base Chain:**
1. pool:base:uniswap-v2:WETH-X402
2. pool:base:uniswap-v2:HOOD-WETH
3. pool:base:uniswap-v2:PUMP-WETH
4. pool:base:uniswap-v2:CRCL-WETH
5. pool:base:uniswap-v2:TRUMP-WETH-1
6. pool:base:uniswap-v2:IP-WETH
7. pool:base:uniswap-v2:IMAGINE-WETH
8. pool:base:uniswap-v2:GRAYSCALE-WETH
9. pool:base:uniswap-v2:WETH-402GATE
10. pool:base:uniswap-v2:TRUMP-WETH-2
11. pool:base:uniswap-v2:GROK-WETH
12. pool:base:uniswap-v2:LIBRA-WETH
13. pool:base:uniswap-v2:TRUMP-WETH-3
14. pool:base:uniswap-v2:LABUBU-WETH
15. pool:base:uniswap-v2:ANI-WETH
16. pool:base:uniswap-v2:COIN-WETH
17. pool:base:uniswap-v2:50501-WETH
18. pool:base:uniswap-v2:STOCK-WETH
19. pool:base:uniswap-v2:WETH-MIKA
20. pool:base:uniswap-v2:WETH-TSLA
21. pool:base:uniswap-v2:MSTR-WETH

**Ethereum:**
22. pool:ethereum:uniswap-v2:BABYGIRL-WETH

### aerodrome_slipstream (6 assets on Base)

1. pool:base:aerodrome-slipstream:AVNT-USDC
2. pool:base:aerodrome-slipstream:WETH-USDC
3. pool:base:aerodrome-slipstream:USDC-VFY
4. pool:base:aerodrome-slipstream:USDC-VELVET
5. pool:base:aerodrome-slipstream:WETH-CBBTC
6. pool:base:aerodrome-slipstream:EMP-WETH

### aerodrome_v1 (4 assets on Base)

1. pool:base:aerodrome-v1:USDC-EMT
2. pool:base:aerodrome-v1:WETH-W
3. pool:base:aerodrome-v1:WETH-TRAC
4. pool:base:aerodrome-v1:EBTC-CBBTC

### lp_beefy_aero or beefy_vault (5 assets)

**Base:**
1. pool:base:beefy:ANON-WETH (use lp_beefy_aero if Aerodrome LP, beefy_vault if single-sided)
2. pool:base:beefy:CLANKER-WETH

**BSC:**
3. pool:bsc:beefy:COAI-USDT-1
4. pool:bsc:beefy:COAI-USDT-2 (duplicate with different APY)

**Sonic:**
5. pool:sonic:beefy:S-USDC

### raydium_amm (5 assets on Solana - PLACEHOLDER)

1. pool:solana:raydium:TURTLE-DEX-USDC
2. pool:solana:raydium:WSOL-NICKEL
3. pool:solana:raydium:USD1-LIBERTY
4. pool:solana:raydium:PIPPIN-USDC
5. pool:solana:raydium:USD1-VALOR

### uniswap_v3 (1 asset on Base)

1. pool:base:uniswap-v3:CGN-USDC

### hyperion (1 asset on Aptos - PLACEHOLDER)

1. pool:aptos:hyperion:APT-AMI

### balancer_v3 (1 asset on Base - PLACEHOLDER)

1. pool:base:balancer-v3:WETH-USDT-USDC

### spectra_v2 (1 asset on Base - PLACEHOLDER)

1. pool:base:spectra-v2:YVBAL-GHO-USR

### vaultcraft (1 asset on Arbitrum - PLACEHOLDER)

1. pool:arbitrum:vaultcraft:VC-WETH

### yield_yak (1 asset on Avalanche - PLACEHOLDER)

1. pool:avalanche:yield-yak:WETH.E-KIGU

### etherex_cl (1 asset on Linea - PLACEHOLDER)

1. pool:linea:etherex-cl:CROAK-WETH

### peapods_finance (1 asset on Sonic - PLACEHOLDER)

1. pool:sonic:peapods:SCUSD

## Implementation Priority

### High Priority (36 assets on Base - EVM compatible)
These can be configured immediately once contract addresses are known:
- 22 Uniswap v2 pools
- 6 Aerodrome Slipstream pools
- 4 Aerodrome v1 pools
- 2 Beefy pools
- 1 Uniswap v3 pool
- 1 Balancer v3 pool (needs implementation)
- 1 Spectra v2 pool (needs implementation)

### Medium Priority (8 EVM assets on other chains)
Requires additional RPC endpoints but uses existing adapters:
- 2 Beefy pools on BSC
- 2 pools on Sonic (1 Beefy, 1 Peapods)
- 1 Vaultcraft on Arbitrum
- 1 Yield Yak on Avalanche
- 1 Etherex CL on Linea
- 1 Uniswap v2 on Ethereum

### Low Priority (6 non-EVM assets)
Requires new SDK implementations:
- 5 Raydium pools on Solana
- 1 Hyperion pool on Aptos

## Configuration Status

✅ **Ready**: Adapters fully implemented
⚠️ **Partial**: Adapters exist but may need contract addresses or testing
❌ **Placeholder**: Adapters are stubs, need full implementation

| Adapter Type | Status | Assets | Notes |
|--------------|--------|--------|-------|
| uniswap_v2 | ✅ Ready | 23 | Fully implemented |
| uniswap_v3 | ⚠️ Partial | 1 | Needs NFT withdrawal logic |
| aerodrome_v1 | ✅ Ready | 4 | Fully implemented |
| aerodrome_slipstream | ⚠️ Partial | 6 | Needs NFT withdrawal logic |
| lp_beefy_aero | ✅ Ready | 0* | Existing adapter |
| beefy_vault | ✅ Ready | 5 | New generic adapter |
| raydium_amm | ❌ Placeholder | 5 | Needs Solana SDK |
| hyperion | ❌ Placeholder | 1 | Needs Aptos SDK |
| balancer_v3 | ❌ Placeholder | 1 | Needs implementation |
| spectra_v2 | ❌ Placeholder | 1 | Needs implementation |
| vaultcraft | ❌ Placeholder | 1 | May use ERC4626 |
| yield_yak | ❌ Placeholder | 1 | May use ERC4626 |
| etherex_cl | ❌ Placeholder | 1 | Similar to Uniswap v3 |
| peapods_finance | ❌ Placeholder | 1 | Lending protocol |

*Can be used for some Beefy pools with LP tokens

## Next Steps

1. **Gather Contract Addresses**: For all 50 assets, collect:
   - Token addresses
   - LP token addresses (for AMMs)
   - Router addresses
   - Vault addresses (for Beefy/yield optimizers)
   - NFT position manager addresses (for concentrated liquidity)

2. **Populate .env File**: Fill in the 150+ environment variables added to .env.example

3. **Update config.json**: Add all 50 pool configurations

4. **Test in Dry-Run Mode**: Use `PORTFOLIO_DRY_RUN=true` to test configurations

5. **Implement Placeholder Adapters**: Complete implementations for:
   - Balancer v3
   - Spectra v2
   - Vaultcraft (check if ERC4626 compatible)
   - Yield Yak (check if ERC4626 compatible)
   - Etherex CL (similar to Uniswap v3)
   - Peapods Finance

6. **Consider Solana/Aptos**: Decide whether to implement non-EVM chains or focus on EVM-compatible assets first
