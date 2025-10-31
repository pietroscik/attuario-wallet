# Adaptive Asset Selection Criteria - Implementation Guide

## Overview

This implementation adds an adaptive asset selection system that automatically adjusts to loop intervals and provides advanced technical analysis for pool selection.

## Key Features

### 1. Adaptive Loop Profiles
The system automatically selects appropriate parameters based on loop interval:

- **5-minute loop**: Fast EMA (12 bars), Slow EMA (36 bars)
- **15-minute loop**: Fast EMA (12 bars), Slow EMA (48 bars)
- **60-minute loop**: Fast EMA (24 bars), Slow EMA (96 bars)
- **Daily loop**: Fast EMA (7 bars), Slow EMA (30 bars)

### 2. Technical Indicators

#### Trend Detection
- **EMA (Exponential Moving Average)**: Fast and slow EMAs for trend identification
- **Slope Analysis**: Log-linear regression on EMA_slow to quantify trend strength
- **MACD-like**: Difference between fast and slow EMAs

#### Risk Metrics
- **Max Drawdown**: Maximum peak-to-trough decline
- **Downside Deviation**: Volatility of negative returns only
- **Realized Returns**: r1 (1-period), r7 (7-period), r30 (30-period)

#### Performance Analysis
- **TWR (Time-Weighted Return)**: Compounded returns over period
- **Log Returns**: Natural logarithm of price ratios
- **APY Gap**: Difference between theoretical and realized APY

### 3. Signal Generation

#### Regime Classification
- **UP**: Positive trend, low drawdown, positive TVL growth
- **FLAT**: No clear trend
- **DOWN**: Negative trend, high drawdown, or negative TVL growth

#### Entry/Exit Signals with Hysteresis
- **Entry Signal**: Requires confirmation over multiple bars (reduces false signals)
- **Exit Signal**: Triggers on regime deterioration or risk threshold breach
- **Holding State**: Maintains position until exit conditions confirmed

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Enable/disable adaptive metrics
ENABLE_ADAPTIVE_METRICS=true

# Loop interval in minutes (5, 15, 60, 1440)
LOOP_INTERVAL_MIN=5

# Minimum annual APY requirement (8% default)
APY_MIN_ANNUAL=0.08

# APY gap tolerance (10% default)
APY_GAP_TOL=0.10

# Optional overrides
#DD_STOP_OVERRIDE=0.18
#VOL_CAP_OVERRIDE=0.03
```

## Integration

### Module Structure

```
bots/wave_rotation/
├── metrics_runtime.py       # Core adaptive metrics engine
├── time_series_data.py      # Time series data collection
├── strategy.py              # Main strategy (enhanced)
└── test_metrics_runtime.py  # Test suite
```

### Usage in Strategy

The integration happens automatically in `select_best_pool()`:

1. **Candidate Enhancement**: Each candidate pool is analyzed with `metrics_runtime`
2. **Signal Computation**: Calculates regime, trend, and risk metrics
3. **Score Adjustment**: 
   - UP regime: +10% score boost
   - DOWN regime or exit signal: -50% score penalty
4. **State Persistence**: Hysteresis state saved for next iteration

### Data Flow

```
Pool Data → collect_pool_time_series() → compute_signals() → Enhanced Pool
    ↓
  Price/TVL/APY Series
    ↓
  EMA/Slope/Drawdown/Volatility
    ↓
  Regime Classification + Entry/Exit Signals
    ↓
  Score Adjustment + Ranking
```

## Logging

Enhanced CSV log includes:

- `signal_regime`: UP/FLAT/DOWN
- `signal_score`: Composite technical score
- `ema_fast`: Fast EMA value
- `ema_slow`: Slow EMA value
- `slope`: Trend slope coefficient
- `r7`: 7-period realized return
- `drawdown`: Maximum drawdown
- `vol_down`: Downside volatility

## Testing

Run the test suite:

```bash
cd bots/wave_rotation
python test_metrics_runtime.py
```

### Test Coverage

- ✅ Loop profile selection (4 profiles)
- ✅ EMA calculation
- ✅ Log returns
- ✅ Max drawdown
- ✅ Downside deviation
- ✅ TWR calculation
- ✅ Slope analysis
- ✅ Realized returns
- ✅ Signal generation
- ✅ Hysteresis behavior
- ✅ Multi-series integration (price/TVL/APY)

## API Reference

### `compute_signals()`

Main function for signal generation.

**Parameters:**
- `price_series` (pd.Series): Price/NAV time series with datetime index
- `tvl_series` (pd.Series, optional): TVL time series
- `apy_series` (pd.Series, optional): APY time series
- `loop_minutes` (int): Loop interval in minutes
- `apy_min` (float): Minimum APY threshold
- `gap_tau` (float): APY gap tolerance
- `prev_state` (Dict, optional): Previous state for hysteresis

**Returns:**
- `SignalResult`: Contains regime, enter/exit signals, score, and info dict
- `LoopProfile`: Selected profile configuration

### `SignalResult` Structure

```python
@dataclass
class SignalResult:
    regime: str           # "UP", "FLAT", or "DOWN"
    enter: bool          # Entry signal triggered
    exit: bool           # Exit signal triggered
    score: float         # Composite technical score
    info: Dict           # Detailed metrics
```

### `info` Dictionary Contents

```python
{
    "ema_fast": float,      # Fast EMA value
    "ema_slow": float,      # Slow EMA value
    "macd": float,          # EMA difference
    "slope": float,         # Trend slope
    "r1": float,            # 1-period return
    "r7": float,            # 7-period return
    "r30": float,           # 30-period return
    "dd": float,            # Max drawdown
    "vol_down": float,      # Downside volatility
    "dTVL7": float,         # 7-period TVL change
    "dAPY": float,          # APY change
    "apy_gap": float,       # Theoretical vs realized gap
    "apy_min": float,       # Minimum APY threshold
    "apy_ok": bool,         # APY threshold met
    "confirm_in": int,      # Entry confirmation count
    "confirm_out": int,     # Exit confirmation count
    "holding": bool,        # Currently holding position
}
```

## Performance Considerations

### Computation Cost
- Minimal overhead: ~50-100ms per pool
- Cached time series data when available
- Synthetic data generation for missing history

### Memory Usage
- Efficient pandas operations
- Limited lookback period (90 days default)
- State persistence in JSON format

## Extending the System

### Adding New Indicators

Add to `metrics_runtime.py`:

```python
def my_indicator(series: pd.Series) -> float:
    # Your calculation
    return result

# Use in compute_signals()
my_value = my_indicator(px)
info['my_indicator'] = my_value
```

### Custom Loop Profiles

Modify `_choose_profile()`:

```python
if m <= 3:  # 3-minute profile
    return LoopProfile(
        loop_minutes=m,
        resample_rule="3min",
        ema_fast_bars=10,
        ema_slow_bars=30,
        ...
    )
```

### Integration with External Data

Enhance `time_series_data.py`:

```python
def fetch_my_data_source(pool_id: str) -> pd.Series:
    # Fetch from your API
    return pd.Series(data, index=dates)
```

## Troubleshooting

### Issue: Signals not generating
**Solution**: Check that `ENABLE_ADAPTIVE_METRICS=true` in `.env`

### Issue: Poor signal quality
**Solution**: 
1. Increase `LOOP_INTERVAL_MIN` for longer-term signals
2. Adjust `APY_MIN_ANNUAL` threshold
3. Check data quality in time series

### Issue: Too many false signals
**Solution**: Increase `confirm_bars_in` in profile settings

## Future Enhancements

Potential improvements:

1. **Real Historical Data**: Integration with DeFiLlama historical API
2. **Machine Learning**: Train models on signal performance
3. **Multi-Timeframe**: Combine signals from multiple timeframes
4. **Sentiment Analysis**: Incorporate on-chain metrics
5. **Risk-Adjusted Scoring**: Sharpe ratio, Sortino ratio integration

## References

- **DeFiLlama API**: https://defillama.com/docs/api
- **Technical Analysis**: Moving averages, MACD, drawdown calculations
- **Time-Weighted Returns**: Standard portfolio performance metric
- **Hysteresis**: Signal confirmation to reduce noise

## Support

For issues or questions:
1. Check test suite: `python test_metrics_runtime.py`
2. Review logs for `[metrics]` prefixed messages
3. Verify environment variables in `.env`
4. Check GitHub workflow runs for validation results
