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
- ✅ **Multi-Asset Support**: Handles ETH, WETH, USDC, EURC, ANON, and 50+ other tokens
- ✅ **Automatic Pool Matching**: Matches wallet assets to compatible pools based on adapter configuration
- ✅ **Greedy Optimization**: Allocates each asset to its highest-scored pool
- ✅ **Buffer Reserve System**: Keeps configurable % of funds unallocated for gas and safety
- ✅ **Dry-Run Mode**: Test allocations without executing transactions
- ✅ **State Persistence**: Logs all allocations to JSON for tracking
- ✅ **Treasury Integration**: Compatible with existing 50% profit split to treasury
- ✅ **Adapter Compatibility**: Works with all existing adapters (Aave, Morpho, Beefy, etc.)

### Optimization Algorithm

The current implementation uses a **greedy algorithm**:
1. Scans wallet for all available assets
2. Matches each asset to compatible pools via adapters
3. Calculates normalized scores for each pool (APY / risk / cost)
4. Allocates each asset to its highest-scored pool
5. Applies buffer reserve (default 5%)
6. Filters by minimum investment threshold

**Future Enhancement**: Linear programming optimization for multi-pool splits per asset.

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Multi-Strategy Optimizer
MULTI_STRATEGY_ENABLED=true          # Enable/disable multi-strategy mode
STRATEGY_BUFFER_PERCENT=5.0          # Percentage of funds to keep as reserve (0-100)
MIN_INVESTMENT_PER_POOL=0.001        # Minimum amount to allocate per pool
MAX_POOLS_PER_ASSET=3                # Maximum pools to consider per asset

# Execution Mode
PORTFOLIO_DRY_RUN=true               # Test without executing (set false for live)
PORTFOLIO_AUTOMATION_ENABLED=true     # Enable portfolio automation

# Treasury Integration
TREASURY_AUTOMATION_ENABLED=true      # Enable automatic treasury transfers
TREASURY_ADDRESS=0x...               # Treasury wallet address
```

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MULTI_STRATEGY_ENABLED` | `false` | Enable multi-strategy mode |
| `STRATEGY_BUFFER_PERCENT` | `5.0` | Reserve buffer (%) |
| `MIN_INVESTMENT_PER_POOL` | `0.001` | Min allocation threshold |
| `MAX_POOLS_PER_ASSET` | `3` | Max pools per asset |
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

# Expected output: "TEST RESULTS: 6 passed, 0 failed"
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
- **Assets**: Handles 50+ tokens simultaneously
- **Pools**: Scans 200+ pools per execution
- **Adapters**: Supports 20+ adapter types
- **Chains**: Multi-chain (Base, Ethereum, Arbitrum, Sonic, etc.)

### Execution Time
- Pool fetching: ~2-5 seconds (cached)
- Matching: <1 second
- Optimization: <1 second
- Execution: 30-60 seconds per pool (blockchain dependent)

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
