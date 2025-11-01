# Multi-Strategy Optimizer Documentation

## Overview

The Multi-Strategy Optimizer is an advanced portfolio management system that automatically allocates wallet funds across multiple DeFi pools based on:
- Asset compatibility
- APY scores
- Risk factors
- Available liquidity (TVL)

This module extends the existing Wave Rotation strategy by supporting simultaneous allocations to multiple pools across different assets.

## Features

### Core Capabilities
- ✅ **Wallet Scanner 2.0**: Normalises ETH/WETH/stablecoin balances in USD and filters “dust” via `MIN_DUST_USD`
- ✅ **Trend-Aware Scoring**: Combines APY, price momentum, volatility and drawdown into a composite score
- ✅ **Net-Edge Validation**: Executes only if expected return (after gas + fees + slippage) exceeds `EDGE_MIN_NET_USD`
- ✅ **Diversified Planner**: Allocates per asset with buffer reserve and max destination cap (`MAX_POOLS_PER_ASSET`)
- ✅ **Dry-Run Friendly**: All logic can run without on-chain mutations
- ✅ **State Persistence**: Allocation snapshots saved to `multi_strategy_state.json`
- ✅ **Adapter Compatibility**: Works with existing adapters (Aave, Morpho, Beefy, Comet, etc.)

### Optimization Flow

1. **Scan** – `wallet_scanner.scan_wallet` gathers balances & USD conversion
2. **Score** – trend metrics (slope, Z-score, volatility, drawdown) drive composite score via `scoring.compute_trend_score`
3. **Plan** – build allocation plan respecting buffers, minimum size and diversification constraints
4. **Edge Check** – estimated net edge must exceed `EDGE_MIN_NET_USD` before inclusion
5. **Execute** – adapters invoked (or simulated) sequentially with nonce protection handled upstream

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Multi-Strategy Optimizer
MULTI_STRATEGY_ENABLED=true            # Enable/disable optimizer
STRATEGY_BUFFER_PERCENT=10.0           # Buffer kept in wallet (percentage)
MIN_INVESTMENT_PER_POOL_USD=100        # Minimum USD chunk per allocation
MAX_POOLS_PER_ASSET=2                  # Diversification cap per asset
MIN_DUST_USD=50                        # Ignore holdings below this value

# Trend / scoring knobs
TREND_WINDOW_D=14
TREND_LOOKBACK_D=90
TREND_Z_MIN=0.5
TREND_Z_CAP=3.0
TREND_VOL_CAP=0.05
TREND_DD_CAP=0.25
W_APY=0.4
W_TR=0.5
W_VOL=0.05
W_DD=0.05

# Net edge parameters
HORIZON_DAYS=1.0
EDGE_MIN_NET_USD=0.5
GAS_WITHDRAW_COST_USD=0.35
GAS_DEPOSIT_COST_USD=0.35
EDGE_INCLUDE_WITHDRAW=true
SWAP_FEE_BPS=5
EDGE_SLIPPAGE_BPS=50

# Execution mode
PORTFOLIO_DRY_RUN=true
PORTFOLIO_AUTOMATION_ENABLED=true
```

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MULTI_STRATEGY_ENABLED` | `false` | Enable multi-strategy mode |
| `STRATEGY_BUFFER_PERCENT` | `5.0` | Reserve buffer (%) |
| `MIN_INVESTMENT_PER_POOL_USD` | `100` | Minimum allocation size in USD |
| `MAX_POOLS_PER_ASSET` | `1` | Max pools per asset |
| `MIN_DUST_USD` | `0.25` | Ignore balances below this value |
| `TREND_WINDOW_D` | `14` | Trend lookback window |
| `EDGE_MIN_NET_USD` | `0.5` | Minimum net expected profit |
| `PORTFOLIO_DRY_RUN` | `true` | Dry-run mode for testing |

## Usage

### Running Multi-Strategy

```bash
# Enable multi-strategy in .env
MULTI_STRATEGY_ENABLED=true

# Run strategy script
cd bots/wave_rotation
python strategy.py
```

### Running Tests

```bash
cd bots/wave_rotation

# Run test suite
python test_multi_strategy.py

# All tests should pass - currently 6 test cases covering:
# - Configuration, pool matching, optimization, execution, state, integration
```

### Running Demonstration

```bash
cd bots/wave_rotation

# Run demo with mock wallet
python demo_multi_strategy.py

# Shows allocation across ETH, WETH, USDC, EURC, ANON
```

## Architecture

### Module Structure

```
multi_strategy.py
├── MultiStrategyConfig         # Configuration loader
├── AllocationPlan              # Allocation plan dataclass
├── match_pools_to_assets()     # Pool-to-asset matching
├── optimize_allocations()      # Optimization algorithm
├── execute_allocations()       # Adapter execution
├── save_allocation_state()     # State persistence
└── execute_multi_strategy()    # Main entry point
```

### Integration with Existing System

```
strategy.py (main)
    ↓
    ├─→ collect_wallet_assets()        # Existing wallet scanner
    ├─→ fetch_pools_scoped()           # Existing pool fetcher
    ├─→ MultiStrategyConfig.load()     # Load multi-strategy config
    └─→ execute_multi_strategy()       # Execute multi-strategy
            ↓
            ├─→ match_pools_to_assets()    # Match assets to pools
            ├─→ optimize_allocations()     # Optimize allocations
            └─→ execute_allocations()      # Execute via adapters
                    ↓
                    └─→ adapter.deposit_all()  # Existing adapters
```

## State File Format

Allocations are saved to `multi_strategy_state.json`:

```json
{
  "timestamp": "2025-10-30 10:44:33",
  "allocations": {
    "WETH": {
      "pool": "base:morpho:WETH",
      "pool_name": "Morpho WETH Vault",
      "chain": "base",
      "amount": 1.9,
      "usd_value": 5700.0,
      "score": 0.000123,
      "apy": 0.045
    },
    "USDC": {
      "pool": "base:morpho:USDC",
      "pool_name": "Morpho USDC Vault",
      "chain": "base",
      "amount": 4750.0,
      "usd_value": 4750.0,
      "score": 0.000191,
      "apy": 0.072
    }
  },
  "buffer_reserved": true,
  "execution_results": {
    "base:morpho:WETH": "ok:0x1234...",
    "base:morpho:USDC": "ok:0x5678..."
  }
}
```

## Example Scenarios

### Scenario 1: Conservative Portfolio

```bash
# .env configuration
MULTI_STRATEGY_ENABLED=true
STRATEGY_BUFFER_PERCENT=10.0      # Higher buffer for safety
MIN_INVESTMENT_PER_POOL=0.1       # Higher minimum
```

**Result**: Allocates only to safest, highest-value pools with 10% buffer reserve.

### Scenario 2: Aggressive Portfolio

```bash
# .env configuration
MULTI_STRATEGY_ENABLED=true
STRATEGY_BUFFER_PERCENT=2.0       # Lower buffer
MIN_INVESTMENT_PER_POOL=0.001     # Lower minimum
MAX_POOLS_PER_ASSET=5             # More diversification
```

**Result**: Allocates more capital across more pools, maximizing deployment.

### Scenario 3: Test Mode

```bash
# .env configuration
MULTI_STRATEGY_ENABLED=true
PORTFOLIO_DRY_RUN=true            # Test mode
STRATEGY_BUFFER_PERCENT=5.0
```

**Result**: Simulates allocations without executing transactions.

## Treasury Integration

The multi-strategy optimizer is fully compatible with the existing treasury automation:

1. **Profit Calculation**: After each interval, profits are calculated per pool
2. **50% Split**: Half goes to treasury (EURC), half is reinvested
3. **Automatic Swap**: ETH profits → EURC via 0x protocol
4. **Transfer**: EURC sent to treasury wallet address

To enable:
```bash
TREASURY_AUTOMATION_ENABLED=true
TREASURY_ADDRESS=0xYourTreasuryWallet
```

## Monitoring and Logs

### State Files
- `multi_strategy_state.json` - Latest allocations
- `log.csv` - Historical execution log (existing)
- `daily.log` - Detailed debug log (existing)

### Telegram Notifications

Multi-strategy sends notifications for:
- ✅ Successful allocations
- ⚠️ No viable allocations found
- 🚨 Execution errors
- 💰 Treasury transfers

Example notification:
```
🎯 Multi-Strategy Allocation Complete

• WETH → Morpho WETH Vault ($5,700.00)
• USDC → Morpho USDC Vault ($4,750.00)

💰 Total: $10,450.00
🔄 Mode: DRY RUN
```

## Troubleshooting

### No Allocations Generated

**Problem**: `multi_strategy_state.json` shows `"allocations": {}`

**Solutions**:
1. Check wallet has sufficient balance: `MIN_INVESTMENT_PER_POOL` threshold
2. Verify adapters are configured in `config.json`
3. Ensure pools are available from data sources
4. Check token addresses match between wallet and adapters

### "No Compatible Pools" Error

**Problem**: Assets don't match any pool adapters

**Solutions**:
1. Add adapter configurations to `config.json`
2. Verify token addresses are correct (lowercase)
3. Check `POOL_ALLOWLIST` / `POOL_DENYLIST` filters
4. Ensure data sources return pools for configured chains

### Dry-Run Always Active

**Problem**: Transactions not executing even with `PORTFOLIO_DRY_RUN=false`

**Solutions**:
1. Enable portfolio automation: `PORTFOLIO_AUTOMATION_ENABLED=true`
2. Enable onchain execution: `ONCHAIN_ENABLED=true`
3. Check gas reserves: `GAS_RESERVE_ETH`
4. Verify private key is configured: `PRIVATE_KEY`

## Performance Considerations

### Scalability
The system is designed to handle:
- **Assets**: Multiple tokens across different chains
- **Pools**: Hundreds of pools from various protocols
- **Adapters**: Multiple adapter types (ERC4626, Aave, Morpho, Beefy, etc.)
- **Chains**: Multi-chain support (Base, Ethereum, Arbitrum, Sonic, etc.)

Actual capacity depends on RPC limits, API rate limits, and network conditions.

### Execution Time
Typical execution times (varies by network conditions and blockchain congestion):
- Pool fetching: ~2-5 seconds (with caching enabled)
- Matching and optimization: <1 second (in-memory operations)
- Transaction execution: 30-60+ seconds per pool (blockchain-dependent)

Note: Performance varies based on RPC endpoint quality, gas prices, and network congestion.

### Gas Optimization
- Batch operations when possible
- Skip unnecessary approvals
- Configurable gas limits
- Gas price monitoring

## Future Enhancements

### Planned Features
1. **Linear Programming Optimization**: Split single assets across multiple pools
2. **Dynamic Rebalancing**: Automatically rebalance based on performance
3. **Risk-Adjusted Allocation**: Weight allocations by risk tolerance
4. **Historical Performance Tracking**: Track ROI per allocation over time
5. **Machine Learning Integration**: Predict optimal allocations using ML

### Extension Points
- Custom scoring algorithms: Override `normalized_score()`
- Custom optimization: Replace greedy with LP solver
- Custom execution: Add pre/post-execution hooks
- Custom state format: Extend `AllocationPlan` dataclass

## Security Considerations

### Best Practices
1. ✅ Always test with `PORTFOLIO_DRY_RUN=true` first
2. ✅ Use conservative `STRATEGY_BUFFER_PERCENT` (≥5%)
3. ✅ Set reasonable `MIN_INVESTMENT_PER_POOL` limits
4. ✅ Monitor allocations via state files
5. ✅ Enable treasury automation for profit protection

### Risk Mitigation
- **Buffer Reserve**: Protects against total capital lock
- **Dry-Run Mode**: Test before live execution
- **Adapter Validation**: Verifies adapter compatibility
- **State Persistence**: Tracks all allocations
- **Error Handling**: Graceful degradation on failures

## Support and Contributing

### Getting Help
- Review this documentation
- Check `demo_multi_strategy.py` for examples
- Run `test_multi_strategy.py` to validate setup
- Check logs in `daily.log`

### Contributing
To extend the multi-strategy optimizer:
1. Fork the repository
2. Create feature branch
3. Add tests in `test_multi_strategy.py`
4. Update this documentation
5. Submit pull request

## References

- Main strategy: `strategy.py`
- Core module: `multi_strategy.py`
- Tests: `test_multi_strategy.py`
- Demo: `demo_multi_strategy.py`
- Config: `.env.example`
