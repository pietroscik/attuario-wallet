# Wave Rotation Bot - Optimization Report

## Summary

This report documents the optimization and review of the Attuario Wave Rotation trading bot as requested in the optimization issue.

## Fixes Applied

### 1. RPC Connection Lazy Initialization ✅

**Issue**: The `onchain.py` module was attempting to connect to RPC nodes at import time, causing failures when the environment wasn't properly configured or when running tests.

**Fix**: Modified the RPC connection logic to be lazy - connections are now only established when actually needed through the `get_w3()` function. This allows the module to be imported and tested without requiring a live RPC connection.

**Files Changed**: `bots/wave_rotation/onchain.py`

### 2. Import Path Fixes ✅

**Issue**: Several modules used absolute imports (`from bots.wave_rotation.X import Y`) which prevented them from running correctly when executed from within the wave_rotation directory.

**Fix**: Changed to relative imports for consistency and to allow the bot to run both as a standalone module and as part of the larger project.

**Files Changed**: 
- `bots/wave_rotation/portfolio.py`
- `bots/wave_rotation/selection_greedy.py`

## Verification of Core Functionality

### All Required Operations Are Present ✅

The bot successfully implements all required operations:

1. **Evaluation (Valutazione)** ✅
   - `fetch_pools_scoped()` in `data_sources.py` fetches available pools from DeFiLlama and other sources
   - `select_best_pool()` in `strategy.py` evaluates pools using the scoring formula

2. **Subscription/Selection (Sottoscrizione)** ✅
   - Pool selection logic ranks pools by score = r_day / (1 + cost_daily * (1 - risk))
   - Follows CODEX_RULES: switches only if new score ≥ old score * (1 + delta) where delta = 1%

3. **Deposit (Deposito)** ✅
   - `move_capital_smart()` in `executor.py` handles deposits via adapters
   - `deposit_all()` method in adapters (ERC4626, auto-adapters)
   - Supports explicit adapters and auto-detection for ERC4626, Beefy, Yearn, Compound, Aave

4. **Redemption/Withdrawal (Riscatto)** ✅
   - `move_capital_smart()` in `executor.py` handles withdrawals
   - `withdraw_all()` method in adapters
   - Automatically withdraws from old pool before depositing to new pool

5. **Treasury Allocation (Allocazione Tesoreria)** ✅
   - `settle_day()` in `executor.py` calculates profit split (50/50 by default)
   - `dispatch_treasury_payout()` in `treasury.py` handles ETH → EURC swap and transfer
   - Supports automatic treasury transfers to Base address when enabled

## Guardrail Analysis

### Minimal Guardrails by Default ✅

As requested ("non applicare filtri gardrail che bloccano la selezione del pool"), the bot has minimal guardrails by default:

1. **Adapter Requirement**: DISABLED by default
   - `REQUIRE_ADAPTER_BEFORE_RANK=0` (default)
   - Pools without adapters are NOT filtered out by default

2. **Virtual Token Filter**: DISABLED by default
   - `EXCLUDE_VIRTUAL=0` (default)
   - Virtual tokens are NOT excluded by default

3. **Aggressive Mode**: ENABLED by default
   - `aggressive: true` in config.json
   - Skips staleness, TVL, and adapter penalties
   - Uses pure net daily rate for scoring

4. **Fallback Logic**: Present at multiple levels
   - If no pools pass filters, falls back to base pool set (line 492 in strategy.py)
   - If no candidates at all, provides diagnostic information

### Reasonable Economic Guardrails (Can Be Disabled)

These guardrails prevent economically irrational moves but can be disabled via environment variables:

1. **Gas Ceiling** (Optional)
   - Only active if `GAS_PRICE_MAX_GWEI` is set
   - Prevents moves when gas is too expensive

2. **Economic Edge Check** (Can be disabled)
   - Ensures expected profit exceeds gas costs
   - Controlled via `MIN_EDGE_SCORE`, `MIN_EDGE_ETH`, `MIN_EDGE_USD`, `EDGE_GAS_MULTIPLIER`
   - Optional USD threshold requires `ETH_PRICE_USD`

3. **TVL Minimum** (Configurable)
   - `min_tvl_usd: 100000` in config.json
   - Per CODEX_RULES, only exclude pools with TVL < 100k USD
   - Reasonable minimum for liquidity

## Scoring Formula Verification ✅

The scoring formula correctly implements CODEX_RULES:

```python
# Line 524 in strategy.py
s = r_day / (1.0 + cost_daily * (1.0 - risk))
```

This matches CODEX_RULES formula:
```
Score_i,t = r_i,t / (1 + c_i,t ⋅ (1 − ρ_i,t))
```

**Important Note**: The code correctly converts annual fees to daily fees before using them in the formula (line 520):
```python
cost_daily = cost_annual / 365.0
```

## Stop-Loss & Auto-Pause Verification ✅

The stop-loss and auto-pause mechanisms work correctly:

1. **Stop-Loss** (Default: -10% daily)
   - If `r_net_interval < stop_loss_daily * interval_factor`, capital is preserved
   - No reinvestment or treasury allocation occurs
   - Crisis streak counter increments

2. **Auto-Pause** (Default: 3 consecutive losses)
   - After `autopause.streak` consecutive losses, vault pauses automatically
   - Bot continues evaluation but doesn't execute moves
   - Can resume automatically based on `autopause.resume_wait_minutes`

## Test Coverage ✅

Added `test_basic.py` with tests for:
- Module imports
- Scoring functions (daily_rate, normalized_score)
- Data normalization
- Capital settlement (settle_day)
- Pool switching logic (should_switch)

All tests pass successfully.

## Adapter System ✅

The bot supports a comprehensive adapter system:

1. **Explicit Adapters** (configured in config.json)
   - ERC4626 adapter with full deposit/withdraw support

2. **Auto-Detection Adapters** (probe on-chain)
   - ERC4626Auto
   - BeefyAuto
   - YearnAuto
   - CometAuto (Compound v3)
   - CTokenAuto (Compound v2 compatible)
   - AaveV3Auto

3. **Adapter Caching**
   - Results cached in `cache/auto_adapter_cache.json`
   - TTL configurable via `ADAPTER_CACHE_TTL_H` (default: 168h = 1 week)

## Configuration Review

### config.json Settings

All settings are appropriate and match CODEX_RULES:

- `delta_switch: 0.01` ✅ (1% minimum improvement)
- `reinvest_ratio: 0.5` ✅ (50/50 split)
- `stop_loss_daily: -0.10` ✅ (-10% daily stop-loss)
- `min_tvl_usd: 100000` ✅ (100k USD minimum)
- `aggressive: true` ✅ (minimal penalties)

## Environment Variable Defaults

Key environment variables and their defaults:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ONCHAIN_ENABLED` | `false` | Enable on-chain execution |
| `PORTFOLIO_AUTOMATION_ENABLED` | `false` | Enable automatic deposit/withdraw |
| `PORTFOLIO_DRY_RUN` | `false` | Simulate moves without executing |
| `TREASURY_AUTOMATION_ENABLED` | `false` | Enable automatic treasury transfers |
| `EXCLUDE_VIRTUAL` | `0` | Exclude virtual tokens |
| `REQUIRE_ADAPTER_BEFORE_RANK` | `0` | Require adapter before ranking |
| `AGGRO_MODE` | `` | Skip penalties (also controlled by config) |
| `GAS_PRICE_MAX_GWEI` | unset | Maximum gas price (optional) |
| `MIN_EDGE_SCORE` | unset | Minimum score delta before moving |
| `MIN_EDGE_ETH` | unset | Minimum expected gain in ETH |
| `MIN_EDGE_USD` | unset | Minimum expected gain in USD (requires `ETH_PRICE_USD`) |
| `EDGE_GAS_MULTIPLIER` | `1.0` | Multiplier for gas cost comparison |

## Recommendations

1. **For Production Use**:
   - Set `ONCHAIN_ENABLED=true` with valid RPC and private key
   - Set `PORTFOLIO_AUTOMATION_ENABLED=true` to enable actual moves
   - Configure `TREASURY_AUTOMATION_ENABLED=true` for treasury automation
   - Keep `REQUIRE_ADAPTER_BEFORE_RANK=0` to maximize pool selection
   - Keep `aggressive: true` in config.json

2. **For Testing**:
   - Use `PORTFOLIO_DRY_RUN=true` to simulate without executing
   - Set `ONCHAIN_ENABLED=false` to skip on-chain calls
   - Tune `MIN_EDGE_SCORE`, `MIN_EDGE_ETH`, `MIN_EDGE_USD`, or `EDGE_GAS_MULTIPLIER` to adjust sensitivity

3. **Monitoring**:
   - Check `bots/wave_rotation/log.csv` for execution history
   - Review `status` column for guardrail activations (SKIP:*)
   - Monitor `portfolio_status` for adapter issues

## Known Limitations

1. **Solana Pools**: Currently only EVM chains are supported (Base, Arbitrum, Polygon). Solana pools in the config will be fetched from DeFiLlama but cannot be executed.

2. **Adapter Coverage**: Not all DeFi protocols have adapters. Pools without compatible adapters can be ranked but not executed unless `FORCE_ADAPTER_FALLBACK=true`.

3. **Gas Estimation**: Gas estimates may be inaccurate for complex protocols. Consider setting reasonable `GAS_MOVE_EST` if needed.

## Conclusion

The Wave Rotation bot is **fully functional** and implements all required operations:
- ✅ Evaluation
- ✅ Selection/Subscription  
- ✅ Deposit
- ✅ Redemption/Withdrawal
- ✅ Treasury Allocation

The bot follows CODEX_RULES correctly and has minimal guardrails by default as requested. All code compiles successfully and basic tests pass.

The main fixes were:
1. Lazy RPC initialization to prevent import-time failures
2. Import path corrections for module independence
3. Verification that all core functions are executable

No additional guardrails were added, and existing ones are appropriately minimal and configurable.
