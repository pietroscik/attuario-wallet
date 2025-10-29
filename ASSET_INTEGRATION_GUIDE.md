# 50 Asset Integration Guide

This document outlines the integration of 50 new asset positions into the Attuario Wallet system.

## Summary

### Adapters Created

#### Fully Implemented (EVM-compatible)
1. **uniswap_v2.py** - Uniswap v2 style AMM pools (22 assets)
2. **uniswap_v3.py** - Uniswap v3 concentrated liquidity (1 asset)
3. **aerodrome_v1.py** - Aerodrome v1 standard AMM (4 assets)
4. **aerodrome_slipstream.py** - Aerodrome concentrated liquidity (6 assets)
5. **beefy_vault.py** - Generic Beefy vault adapter (extends existing lp_beefy_aero)

#### Placeholder/Partial Implementation (Non-EVM or Complex)
6. **raydium_amm.py** - Solana-based (5 assets) - Requires solana-py
7. **hyperion.py** - Aptos-based (1 asset) - Requires aptos-sdk
8. **balancer_v3.py** - Multi-token pools (1 asset)
9. **spectra_v2.py** - Yield tokenization (1 asset)
10. **vaultcraft.py** - Arbitrum vaults (1 asset)
11. **yield_yak.py** - Avalanche aggregator (1 asset)
12. **etherex_cl.py** - Linea concentrated liquidity (1 asset)
13. **peapods_finance.py** - Sonic lending (1 asset)

## Asset Distribution by Chain

- **Base**: 36 assets (Most ready to integrate)
- **Solana**: 5 assets (Requires Solana SDK)
- **BSC**: 2 assets (EVM-compatible, needs BSC RPC)
- **Sonic**: 2 assets (New chain, needs RPC and contracts)
- **Aptos**: 1 asset (Requires Aptos SDK)
- **Avalanche**: 1 asset (EVM-compatible, needs Avalanche RPC)
- **Arbitrum**: 1 asset (EVM-compatible)
- **Linea**: 1 asset (EVM-compatible)
- **Ethereum**: 1 asset (EVM-compatible)

## Next Steps

### Phase 1: Base Chain Integration (Priority)

Base has 36 assets and existing infrastructure. These are ready to configure once contract addresses are known:

#### Uniswap v2 on Base (22 pools)
Configure these in `config.json`:
- WETH-X402, HOOD-WETH, PUMP-WETH, CRCL-WETH, TRUMP-WETH (appears 3 times)
- MSTR-WETH, IP-WETH, IMAGINE-WETH, GRAYSCALE-WETH, WETH-402GATE
- GROK-WETH, LIBRA-WETH, LABUBU-WETH, ANI-WETH, COIN-WETH
- 50501-WETH, STOCK-WETH, WETH-MIKA, WETH-TSLA

Each needs:
```json
"pool:base:uniswap-v2:TOKEN-WETH": {
  "type": "uniswap_v2",
  "router": "${UNISWAP_V2_ROUTER_BASE}",
  "lp_token": "${TOKEN_WETH_LP_ADDRESS}",
  "token0": "${TOKEN_ADDRESS}",
  "token1": "${WETH_TOKEN_ADDRESS}",
  "slippage_bps": 100
}
```

#### Aerodrome Slipstream on Base (6 pools)
- AVNT-USDC, WETH-USDC, USDC-VFY, USDC-VELVET, WETH-CBBTC, EMP-WETH

Each needs:
```json
"pool:base:aerodrome-slipstream:TOKEN-PAIR": {
  "type": "aerodrome_slipstream",
  "nft_manager": "${AERODROME_SLIPSTREAM_NFT_MANAGER}",
  "token0": "${TOKEN0_ADDRESS}",
  "token1": "${TOKEN1_ADDRESS}",
  "tick_spacing": 200,
  "slippage_bps": 50
}
```

#### Aerodrome v1 on Base (4 pools)
- USDC-EMT, WETH-W, WETH-TRAC, EBTC-CBBTC

Each needs:
```json
"pool:base:aerodrome-v1:TOKEN-PAIR": {
  "type": "aerodrome_v1",
  "router": "${AERODROME_ROUTER_8453}",
  "lp_token": "${LP_TOKEN_ADDRESS}",
  "token0": "${TOKEN0_ADDRESS}",
  "token1": "${TOKEN1_ADDRESS}",
  "stable": false,
  "slippage_bps": 50
}
```

#### Beefy on Base (2 pools)
- ANON-WETH, CLANKER-WETH

Use existing `lp_beefy_aero` adapter or new `beefy_vault` adapter depending on vault type.

#### Uniswap v3 on Base (1 pool)
- CGN-USDC

#### Balancer v3 on Base (1 pool)
- WETH-USDT-USDC (3-token pool)

#### Spectra v2 on Base (1 pool)
- YVBAL-GHO-USR

### Phase 2: Multi-Chain EVM Integration

These chains are EVM-compatible and can use existing adapters with proper RPC configuration:

#### BSC (Binance Smart Chain)
- 2 Beefy pools: COAI-USDT (appears twice with different TVL/APY)
- Needs: BSC RPC URL, Beefy vault addresses

#### Arbitrum
- 1 Vaultcraft pool: VC-WETH
- Needs: Arbitrum RPC, Vaultcraft vault address

#### Avalanche
- 1 Yield Yak pool: WETH.E-KIGU
- Needs: Avalanche RPC, Yield Yak vault address

#### Linea
- 1 Etherex CL pool: CROAK-WETH
- Needs: Linea RPC, Etherex position manager address

#### Ethereum Mainnet
- 1 Uniswap v2 pool: BABYGIRL-WETH
- Needs: Ethereum RPC (expensive gas)

#### Sonic
- 2 pools: Beefy S-USDC, Peapods Finance SCUSD
- Needs: Sonic RPC URLs, protocol contract addresses

### Phase 3: Non-EVM Integration (Advanced)

These require different SDK implementations:

#### Solana (5 Raydium pools)
- TURTLE-DEX-USDC, WSOL-NICKEL, USD1-LIBERTY, PIPPIN-USDC, USD1-VALOR
- Requires: solana-py, anchorpy, Raydium SDK integration

#### Aptos (1 Hyperion pool)
- APT-AMI
- Requires: aptos-sdk, Hyperion protocol integration

## Environment Variables to Add

Add to `.env.example`:

```bash
# === UNISWAP V2 ON BASE ===
UNISWAP_V2_ROUTER_BASE=0x... # BaseSwap or other Uniswap v2 fork router
# LP token addresses for each pool
WETH_X402_LP=0x...
HOOD_WETH_LP=0x...
# ... (add all 22 LP tokens)

# === UNISWAP V3 ON BASE ===
UNISWAP_V3_NFT_MANAGER_BASE=0x...
CGN_USDC_POOL=0x...

# === AERODROME ===
AERODROME_SLIPSTREAM_NFT_MANAGER=0x...
# Token addresses for new pairs
EMT_TOKEN=0x...
AVNT_TOKEN=0x...
VFY_TOKEN=0x...
VELVET_TOKEN=0x...
EMP_TOKEN=0x...
# ... (add all new tokens)

# === MULTI-CHAIN RPC ENDPOINTS ===
BSC_RPC=https://bsc-dataseed.binance.org/
SONIC_RPC=https://...
AVALANCHE_RPC=https://api.avax.network/ext/bc/C/rpc
ARBITRUM_RPC=https://arb1.arbitrum.io/rpc
LINEA_RPC=https://rpc.linea.build
SOLANA_RPC=https://api.mainnet-beta.solana.com
APTOS_RPC=https://fullnode.mainnet.aptoslabs.com/v1

# === CHAIN-SPECIFIC PROTOCOL ADDRESSES ===
# BSC
BEEFY_COAI_USDT_VAULT_BSC=0x...

# Sonic
BEEFY_S_USDC_VAULT_SONIC=0x...
PEAPODS_SCUSD_MARKET_SONIC=0x...

# Arbitrum
VAULTCRAFT_VC_WETH_VAULT=0x...

# Avalanche
YIELD_YAK_WETH_KIGU_VAULT=0x...

# Linea
ETHEREX_CL_NFT_MANAGER_LINEA=0x...
CROAK_TOKEN_LINEA=0x...

# Ethereum
UNISWAP_V2_ROUTER_ETHEREUM=0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D
BABYGIRL_TOKEN=0x...
BABYGIRL_WETH_LP=0x...
```

## Configuration Template

Add pools to `config.json` under the `adapters` section. Example template:

```json
{
  "adapters": {
    "pool:base:uniswap-v2:WETH-X402": {
      "type": "uniswap_v2",
      "router": "${UNISWAP_V2_ROUTER_BASE}",
      "lp_token": "${WETH_X402_LP}",
      "token0": "${WETH_TOKEN_ADDRESS}",
      "token1": "${X402_TOKEN}",
      "slippage_bps": 100
    }
    // ... add 49 more pool configurations
  }
}
```

## Testing Strategy

1. **Unit Tests**: Test each adapter's deposit/withdraw logic
2. **Integration Tests**: Test with mainnet fork or testnet
3. **Dry Run Mode**: Use `PORTFOLIO_DRY_RUN=true` to test without real transactions
4. **Phased Rollout**:
   - Phase 1: Base chain only (36 assets)
   - Phase 2: Other EVM chains (8 assets)
   - Phase 3: Non-EVM chains (6 assets)

## Known Limitations

1. **Uniswap v3/Aerodrome Slipstream**: Current implementation doesn't handle withdrawal (NFT position management needed)
2. **Solana/Aptos**: Placeholder implementations - require separate SDK integration
3. **Contract Addresses**: Issue doesn't provide specific addresses - need to source these from:
   - Protocol documentation
   - Chain explorers
   - DefiLlama API
   - Protocol APIs

4. **Gas Costs**: Multi-chain operations will have varying gas costs
5. **RPC Rate Limits**: May need private RPC endpoints for production

## Recommendations

1. **Start with Base Chain**: 36 assets are on Base with existing infrastructure
2. **Use DefiLlama API**: Fetch pool addresses dynamically where possible
3. **Implement Gradual Rollout**: Don't enable all 50 at once
4. **Add Position Tracking**: Especially for NFT-based positions (Uniswap v3, Slipstream)
5. **Consider Gas Optimization**: Batch operations where possible
6. **Add Circuit Breakers**: Implement safety limits for new pools
7. **Monitor APY Accuracy**: Verify reported APYs match actual returns

## Security Considerations

1. **Contract Verification**: Verify all contract addresses on explorers
2. **Allowance Management**: Use `ALLOWANCE_MODE=EXACT` for testing
3. **Slippage Protection**: Adjust `slippage_bps` per pool volatility
4. **Emergency Shutdown**: Implement pause mechanism for new adapters
5. **Audit Requirements**: New adapters handling significant value should be audited
