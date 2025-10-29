# 50 Asset Integration - Action Checklist

Use this checklist to track progress implementing the 50 new assets.

## ✅ Phase 0: Framework Setup (COMPLETED)

- [x] Create 13 new adapter types
- [x] Register adapters in `adapters/__init__.py`
- [x] Update `strategy.py` with token fields
- [x] Add 150+ environment variables to `.env.example`
- [x] Create documentation (4 guides)
- [x] Create validation script
- [x] Create sample configurations
- [x] Test adapter imports

**Status: 100% Complete** ✅

---

## 📋 Phase 1: Base Chain Integration (36 assets)

### Step 1: Gather Contract Addresses

Collect addresses for all Base chain assets:

#### Uniswap v2 Style Pools (22 pools)
- [ ] Get BaseSwap or Uniswap v2 router address on Base
- [ ] WETH-X402: LP token + X402 token addresses
- [ ] HOOD-WETH: LP token + HOOD token addresses
- [ ] PUMP-WETH: LP token + PUMP token addresses
- [ ] CRCL-WETH: LP token + CRCL token addresses
- [ ] TRUMP-WETH (3 instances): LP tokens + TRUMP token
- [ ] MSTR-WETH: LP token + MSTR token addresses
- [ ] IP-WETH: LP token + IP token addresses
- [ ] IMAGINE-WETH: LP token + IMAGINE token addresses
- [ ] GRAYSCALE-WETH: LP token + GRAYSCALE token
- [ ] WETH-402GATE: LP token + 402GATE token
- [ ] GROK-WETH: LP token + GROK token addresses
- [ ] LIBRA-WETH: LP token + LIBRA token addresses
- [ ] LABUBU-WETH: LP token + LABUBU token addresses
- [ ] ANI-WETH: LP token + ANI token addresses
- [ ] COIN-WETH: LP token + COIN token addresses
- [ ] 50501-WETH: LP token + 50501 token addresses
- [ ] STOCK-WETH: LP token + STOCK token addresses
- [ ] WETH-MIKA: LP token + MIKA token addresses
- [ ] WETH-TSLA: LP token + TSLA token addresses

**Sources:**
- BaseScan: https://basescan.org/
- DefiLlama: https://defillama.com/
- Protocol UIs (inspect network tab)

#### Aerodrome Slipstream (6 pools)
- [ ] Get Aerodrome Slipstream NFT Position Manager address
- [ ] AVNT-USDC: AVNT token address, tick parameters
- [ ] WETH-USDC: tick parameters (already have token addresses)
- [ ] USDC-VFY: VFY token address, tick parameters
- [ ] USDC-VELVET: VELVET token address, tick parameters
- [ ] WETH-CBBTC: tick parameters (already have token addresses)
- [ ] EMP-WETH: EMP token address, tick parameters

**Source:** https://aerodrome.finance/

#### Aerodrome v1 (4 pools)
- [ ] Get Aerodrome v1 router address (likely same as existing)
- [ ] USDC-EMT: LP token + EMT token addresses
- [ ] WETH-W: LP token + W token addresses
- [ ] WETH-TRAC: LP token + TRAC token addresses
- [ ] EBTC-CBBTC: LP token + EBTC token addresses

#### Beefy Vaults (2 pools)
- [ ] ANON-WETH: Beefy vault address + ANON token
- [ ] CLANKER-WETH: Beefy vault address + CLANKER token

**Source:** https://app.beefy.com/ (filter by Base)

#### Uniswap v3 (1 pool)
- [ ] Get Uniswap v3 NFT Position Manager on Base
- [ ] CGN-USDC: CGN token address, pool parameters

#### Other Protocols on Base (2 pools)
- [ ] Balancer v3: WETH-USDT-USDC pool ID + vault address
- [ ] Spectra v2: YVBAL-GHO-USR principal + yield token addresses

### Step 2: Populate .env File

```bash
# 1. Make a copy
cp .env.example .env

# 2. Fill in Base chain variables
# Open .env and fill in all addresses gathered in Step 1
nano .env  # or your preferred editor

# 3. Validate format
# Ensure all addresses start with 0x and are 42 characters
# Verify on BaseScan before proceeding
```

### Step 3: Update config.json

```bash
# 1. Backup existing config
cp bots/wave_rotation/config.json bots/wave_rotation/config.json.backup

# 2. Merge configurations
# Open config_sample_50_pools.json
# Copy Base chain pool entries
# Paste into config.json under "adapters" section

# 3. Validate JSON syntax
python3 -m json.tool bots/wave_rotation/config.json > /dev/null
```

### Step 4: Validate Configuration

```bash
cd bots/wave_rotation
python3 validate_50_assets.py

# Expected output:
# ✅ Adapters registered: Yes
# ✅ Base chain pools: 36/36 configured
# ⚠️  Other chains: 0/14 configured (expected)
```

### Step 5: Test in Dry-Run Mode

```bash
# Set dry-run mode
export PORTFOLIO_DRY_RUN=true
export TREASURY_AUTOMATION_ENABLED=false

# Run strategy
python3 strategy.py

# Check logs
tail -f daily.log

# Verify pools appear in scan/score output
```

**Estimated Time:** 2-4 hours (mostly address gathering)

---

## 📋 Phase 2: Other EVM Chains (8 assets)

### BSC Chain (2 assets)
- [ ] Setup BSC RPC endpoint
- [ ] COAI-USDT (2 instances): Beefy vault addresses + COAI token
- [ ] Populate BSC variables in .env
- [ ] Add BSC pools to config.json
- [ ] Test with BSC RPC

### Sonic Chain (2 assets)
- [ ] Setup Sonic RPC endpoint
- [ ] S-USDC: Beefy vault address
- [ ] SCUSD: Peapods Finance market address
- [ ] Populate Sonic variables in .env
- [ ] Add Sonic pools to config.json
- [ ] Test with Sonic RPC

### Arbitrum (1 asset)
- [ ] Setup Arbitrum RPC
- [ ] VC-WETH: Vaultcraft vault address
- [ ] Check if ERC4626 compatible
- [ ] Add to config.json

### Avalanche (1 asset)
- [ ] Setup Avalanche RPC
- [ ] WETH.E-KIGU: Yield Yak vault address
- [ ] Check if ERC4626 compatible
- [ ] Add to config.json

### Linea (1 asset)
- [ ] Setup Linea RPC
- [ ] CROAK-WETH: Etherex CL position manager + CROAK token
- [ ] Add to config.json

### Ethereum (1 asset)
- [ ] Setup Ethereum RPC (expensive gas - use carefully)
- [ ] BABYGIRL-WETH: LP token + BABYGIRL token
- [ ] Add to config.json

**Estimated Time:** 1-2 hours per chain

---

## 📋 Phase 3: Non-EVM Chains (Optional - 6 assets)

### Solana (5 assets)
- [ ] Decide if Solana integration is needed
- [ ] Install solana-py and anchorpy
- [ ] Implement Raydium AMM adapter
- [ ] Get Raydium pool IDs
- [ ] Test on Solana devnet first

### Aptos (1 asset)
- [ ] Decide if Aptos integration is needed
- [ ] Install aptos-sdk
- [ ] Implement Hyperion adapter
- [ ] Get Hyperion pool address
- [ ] Test on Aptos testnet first

**Estimated Time:** 1-2 days per chain

---

## 🎯 Success Criteria

### When Phase 1 Complete:
- [ ] All 36 Base pools visible in `strategy.py` scan output
- [ ] Pools calculate valid APY scores
- [ ] Can allocate capital in dry-run mode
- [ ] No errors in logs

### When Phase 2 Complete:
- [ ] All 44 EVM pools (Base + other chains) operational
- [ ] Multi-chain RPC working correctly
- [ ] Gas costs reasonable for all chains

### When Phase 3 Complete (Optional):
- [ ] All 50 pools integrated
- [ ] Non-EVM chains functional
- [ ] Full multi-chain portfolio

---

## 🛠️ Troubleshooting

### Common Issues

**Issue:** "Adapter init error"
- **Fix:** Check that all required env vars are set
- **Verify:** Run `validate_50_assets.py`

**Issue:** "No assets found"
- **Fix:** Ensure wallet has token balances
- **Note:** For testing, use dry-run mode

**Issue:** "Unknown adapter type"
- **Fix:** Ensure adapter is registered in `ADAPTER_TYPES`
- **Verify:** Check `adapters/__init__.py`

**Issue:** "RPC connection failed"
- **Fix:** Verify RPC URL in .env
- **Check:** RPC provider status page
- **Alternative:** Try different RPC provider

### Getting Help

1. Check documentation in `/ASSET_INTEGRATION_GUIDE.md`
2. Review adapter source code
3. Run validation script
4. Check logs in `daily.log`

---

## 📊 Progress Tracking

**Overall Progress:**

- Phase 0 (Framework): 100% ✅
- Phase 1 (Base Chain): ___% (0/36 pools configured)
- Phase 2 (Other EVM): ___% (0/8 pools configured)
- Phase 3 (Non-EVM): ___% (optional)

**Total Assets Integrated: 0 / 50**

Update this checklist as you complete each item!

---

## 🎉 Completion

When all phases are complete:

1. [ ] Run full validation: `python3 validate_50_assets.py`
2. [ ] Test in dry-run mode for 24 hours
3. [ ] Monitor gas costs and RPC usage
4. [ ] Enable live mode gradually (start with small amounts)
5. [ ] Monitor first rotation cycle
6. [ ] Document any issues encountered
7. [ ] Share results with team

**Congratulations on integrating 50 new assets! 🚀**
