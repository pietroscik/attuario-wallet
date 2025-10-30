# 📘 Attuario Wallet – On-Chain Portfolio Management & DeFi Automation

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Web3](https://img.shields.io/badge/Web3-DeFi-green.svg)](https://web3py.readthedocs.io/)
[![License](https://img.shields.io/badge/License-ISC-yellow.svg)](./contracts/package.json)
[![Base Chain](https://img.shields.io/badge/Chain-Base-0052FF.svg)](https://base.org)

## 🎯 Introduction

**Attuario Wallet** is an advanced on-chain portfolio management system designed for automated DeFi yield optimization. The project implements the **Wave Rotation Strategy**, a dynamic capital allocation algorithm that continuously evaluates DeFi pools across multiple chains and protocols, automatically rotating capital to maximize risk-adjusted returns.

### Key Features

- **Multi-Protocol Support**: Integrates with 20+ DeFi protocols including Aave v3, Morpho Blue, Compound v3, Yearn, Beefy, Aerodrome, and more
- **Cross-Chain Compatibility**: Supports Base, Arbitrum, Ethereum, Polygon, Avalanche, Linea, BSC, Sonic, Solana, and Aptos
- **Automated Yield Optimization**: Evaluates pools every 5-15 minutes using a sophisticated scoring algorithm
- **Treasury Management**: Automatically splits profits 50/50 between reinvestment and treasury allocation
- **Modular Adapter System**: Protocol-specific adapters enable seamless deposits and withdrawals
- **Economic Edge Calculation**: Gas-aware decision making ensures profitable rebalancing
- **Risk Management**: Built-in stop-loss (-10%), configurable risk filters, and autopause mechanisms

## ⚙️ Architecture Overview

The Attuario Wallet consists of several interconnected components working together to provide autonomous portfolio management:

### Core Components

```
attuario-wallet/
├── bots/wave_rotation/          # Main strategy implementation
│   ├── strategy.py              # Wave Rotation entrypoint & orchestration
│   ├── portfolio.py             # Portfolio automation (deposit/withdraw)
│   ├── executor.py              # Capital movement execution logic
│   ├── scoring.py               # Pool scoring & ranking algorithm
│   ├── data_sources.py          # Multi-chain yield data fetching (DefiLlama, APIs)
│   ├── selection_greedy.py      # Greedy pool selection with economic edge
│   ├── treasury.py              # Treasury payout & profit distribution
│   ├── onchain.py               # Web3 layer (RPC, transactions, signing)
│   ├── ops_guard.py             # Gas ceiling & operational safety checks
│   ├── adapters/                # Protocol-specific deposit/withdraw handlers
│   │   ├── aave_v3.py           # Aave v3 lending markets
│   │   ├── erc4626.py           # ERC-4626 vaults (Morpho, Yearn, etc.)
│   │   ├── comet.py             # Compound v3 (Comet) markets
│   │   ├── ctoken.py            # Compound v2 style (Moonwell)
│   │   ├── beefy_vault.py       # Beefy auto-compounding vaults
│   │   ├── lp_beefy_aero.py     # Aerodrome LP + Beefy farming
│   │   ├── aerodrome_v1.py      # Aerodrome v1 AMM pools
│   │   ├── aerodrome_slipstream.py  # Aerodrome concentrated liquidity
│   │   ├── uniswap_v2.py        # Uniswap v2 style DEX pools
│   │   ├── uniswap_v3.py        # Uniswap v3 concentrated liquidity
│   │   ├── raydium_amm.py       # Solana Raydium AMM
│   │   └── ...                  # Additional protocol adapters
│   ├── adapters_auto/           # Auto-detection & ABI resolution
│   ├── config.json              # Pool configurations & adapter settings
│   └── state.json               # Runtime state persistence (gitignored)
├── contracts/                   # Smart contracts (Hardhat)
│   ├── contracts/AttuarioVault.sol  # On-chain vault contract
│   └── ...
├── scripts/
│   ├── codex_entrypoint.sh      # CI/CD execution entrypoint
│   ├── run_daily.sh             # Scheduled daily execution
│   └── run_wave_rotation_loop.sh    # Continuous loop execution
├── .env.example                 # Environment variable template
└── README.md                    # This file
```

### Component Interactions

1. **Data Layer**: `data_sources.py` fetches pool data from DefiLlama, protocol-specific APIs (Aerodrome, Kamino), and on-chain sources
2. **Scoring Engine**: `scoring.py` computes risk-adjusted scores using the formula: `Score = r / (1 + c·(1-ρ))`
3. **Selection**: `selection_greedy.py` ranks pools by economic edge (net profit after gas costs)
4. **Execution**: `portfolio.py` orchestrates withdrawals from current positions and deposits into new pools via adapters
5. **On-Chain**: `onchain.py` handles Web3 interactions, transaction signing, and RPC communication
6. **Treasury**: `treasury.py` manages profit distribution (50% reinvest, 50% treasury)
7. **Persistence**: `state.json` tracks current positions, capital, and execution history

### Adapter Modularity

The adapter system is the heart of protocol integration. Each adapter implements a standard interface:

- `deposit(amount)`: Deploy capital into a specific pool
- `withdraw(amount)`: Exit position and return capital
- `balance()`: Query current position value
- Protocol-specific logic for token approvals, LP operations, staking, etc.

**Supported Adapter Types**:
- `aave_v3`: Aave v3 lending pools
- `erc4626`: ERC-4626 standard vaults (Morpho, Yearn, Spark, Seamless, Moonwell Flagship, Steakhouse)
- `comet`: Compound v3 markets
- `ctoken`: Compound v2 style markets (Moonwell, Sonne)
- `yearn`: Yearn vault integration
- `beefy_vault`: Beefy auto-compounding vaults
- `lp_beefy_aero`: Aerodrome LP + Beefy farming
- `aerodrome_v1`: Aerodrome standard AMM
- `aerodrome_slipstream`: Aerodrome concentrated liquidity
- `uniswap_v2`: Uniswap v2 style pools
- `uniswap_v3`: Uniswap v3 concentrated liquidity
- `raydium_amm`: Solana Raydium AMM
- `hyperion`: Aptos Hyperion pools
- `balancer_v3`: Balancer v3 multi-token pools
- `spectra_v2`: Spectra yield tokenization
- `vaultcraft`: VaultCraft yield vaults
- `yield_yak`: Yield Yak aggregator
- `etherex_cl`: Etherex concentrated liquidity
- `peapods_finance`: PeaPods lending

## 💼 Strategy Logic

### Wave Rotation Strategy

The **Wave Rotation** strategy is a systematic yield optimization approach that evaluates pools at regular intervals and rotates capital to the highest-scoring opportunity.

#### Scoring Algorithm

Each pool is scored using a risk-adjusted return formula:

```
Score_i = r_i / (1 + c_i · (1 - ρ_i))
```

Where:
- **r_i**: Daily return rate (derived from APY: `r ≈ (1 + APY)^(1/365) - 1`)
- **c_i**: Operational cost (gas + fees + slippage) as a percentage of capital
- **ρ_i**: Protocol risk proxy in [0, 1] (0 = high risk, 1 = low risk)

#### Rotation Logic

1. **Continuous Monitoring**: Evaluate all eligible pools every 5-15 minutes (configurable)
2. **Economic Edge Check**: Calculate net profit after gas costs for potential moves
3. **Switch Threshold**: Rotate capital only if new pool score ≥ current score × 1.01 (1% minimum improvement)
4. **Execution**: Withdraw from current position → Deposit into new pool (via adapters)
5. **Gas Optimization**: Skip rotation if gas costs exceed expected profit

#### Profit Distribution (50/50 Rule)

At the end of each day:
1. Calculate daily profit: `P = C₀ · r_net`
2. **Reinvestment**: 50% of profit added to capital: `C₁ = C₀ + 0.5P`
3. **Treasury**: 50% of profit converted to USDC and sent to treasury address

#### Risk Management

- **Stop-Loss**: -10% daily loss threshold triggers autopause for affected positions
- **Take-Profit**: +5% daily gain is captured automatically via 50/50 split
- **Autopause**: After 3 consecutive losses, system pauses and waits 6 hours before resuming
- **TVL Filter**: Excludes pools with TVL < $100,000 (configurable)
- **Gas Ceiling**: Prevents execution if gas prices exceed configured limits

### Security & Production Hardening (Q4 2025)

The system includes multiple security layers for production-ready operation:

#### **Concurrency Protection**
- **Run-Lock**: Prevents concurrent strategy executions using file-based locking
- **Nonce Manager**: Tracks transaction nonces to avoid "nonce too low" errors
- **Idempotent Operations**: Safe retry logic prevents duplicate transactions

#### **Error Handling & Recovery**
- **Kill-Switch**: Automatically halts execution after N consecutive on-chain errors (default: 3)
- **Transaction Error Classification**: Categorizes errors (nonce, gas, revert, slippage, etc.)
- **Revert Decoding**: Extracts human-readable error messages from failed transactions
- **Exponential Backoff**: Automatic retry with increasing delays for transient failures

#### **Slippage & Price Protection**
- **Slippage Bounds**: Configurable slippage tolerance (default: 1%) for all swaps and deposits
- **Min Amount Out**: Enforces minimum output amounts to prevent sandwich attacks
- **Price Impact Limits**: Rejects transactions with excessive price impact (default: 5%)

#### **Protocol State Monitoring**
- **Paused Detection**: Checks if vaults/protocols are paused before depositing
- **Shutdown Detection**: Detects emergency shutdown states (Yearn, Beefy, ERC-4626)
- **Max Deposit Checks**: Validates deposit limits before attempting operations

#### **Safe Math & Decimal Handling**
- **Decimal Validation**: Safely handles non-standard token decimals (0-77 range)
- **Amount Clamping**: Ensures amounts never exceed available balances
- **Rounding**: Uses ROUND_DOWN to prevent balance overflows
- **Fee-on-Transfer Support**: Detects tokens with transfer fees

#### **Allowance Policy**
- **Exact Approvals**: Uses exact amount approvals for non-trusted protocols
- **Max Approvals**: Uses max uint256 approvals only for blue-chip protocols (configurable)
- **Auto-Revoke**: Revokes allowances after withdrawal from non-trusted vaults
- **Allowance Reuse Warning**: Tracks and warns when reusing existing allowances

#### **Execution Summary**
- **Structured Logging**: JSON-formatted execution summaries for observability
- **Gas Tracking**: Records gas used and gas costs for each operation
- **PnL Reporting**: Calculates and reports realized profit/loss
- **Treasury Status**: Tracks treasury movements and reasons for transfers
- **Error/Warning Counts**: Aggregates errors and warnings for monitoring

#### Selection & Ranking

The `selection_greedy.py` module implements economic edge-based ranking:

```python
Net Gain (EUR) = (Score_new - Score_current) × Capital × (Horizon / 24) - Gas Cost
```

Pools are ranked by net gain, ensuring only profitable moves are executed.

## 🔐 Configuration & Environment

### Environment Variables

Copy `.env.example` to `.env` and configure the following variables:

#### Core Settings

```bash
# RPC Endpoints
BASE_RPC=https://mainnet.base.org
ETHEREUM_RPC=https://eth.llamarpc.com
ARBITRUM_RPC=https://arb1.arbitrum.io/rpc
POLYGON_RPC=https://polygon-rpc.com
SOLANA_RPC=https://api.mainnet-beta.solana.com
APTOS_RPC=https://fullnode.mainnet.aptoslabs.com/v1

# Wallet Configuration
PRIVATE_KEY=your_private_key_here
VAULT_ADDRESS=0x0000000000000000000000000000000000000000

# On-Chain Execution
ONCHAIN_ENABLED=false           # Set to true for live execution
PORTFOLIO_AUTOMATION_ENABLED=false  # Enable automated deposits/withdrawals
PORTFOLIO_DRY_RUN=true          # Set to false for real transactions
```

#### Data Sources

```bash
# Yield Data APIs
DEFILLAMA_API=https://yields.llama.fi
AERODROME_API=https://api.aerodrome.finance
KAMINO_API=https://api.kamino.finance

# Data Source Mode
DATA_SOURCE_MODE=PREFER_CACHE   # Options: PREFER_CACHE, LIVE, FALLBACK
```

#### Strategy Parameters

```bash
# Economic Edge
MIN_EDGE_SCORE=0                # Minimum score improvement required
MIN_EDGE_ETH=0                  # Minimum profit in ETH
MIN_EDGE_USD=0                  # Minimum profit in USD
ETH_PRICE_USD=3000              # ETH price for calculations
EDGE_GAS_MULTIPLIER=1.0         # Gas cost multiplier for safety margin

# Pool Filters
POOL_ALLOWLIST=                 # Comma-separated pool IDs to whitelist
POOL_DENYLIST=                  # Comma-separated pool IDs to blacklist
REQUIRE_ADAPTER_BEFORE_RANK=1   # Only rank pools with configured adapters
```

#### Security & Error Handling

```bash
# Kill-Switch Configuration
KILL_SWITCH_THRESHOLD=3         # Consecutive errors before halt
KILL_SWITCH_RESET_TIMEOUT=3600  # Seconds before error counter resets

# Transaction Retry Policy
TX_RETRY_MAX_ATTEMPTS=3         # Maximum retry attempts
TX_RETRY_INITIAL_DELAY=1.0      # Initial delay in seconds
TX_RETRY_MAX_DELAY=30.0         # Maximum delay between retries
TX_RETRY_EXPONENTIAL_BASE=2.0   # Exponential backoff base
TX_RETRY_JITTER=true            # Add random jitter to delays

# Slippage Protection
SLIPPAGE_BPS=100                # Slippage tolerance in basis points (1%)
MAX_PRICE_IMPACT_BPS=500        # Maximum price impact (5%)
MIN_OUTPUT_RATIO=0.95           # Minimum output ratio (95% of expected)

# Allowance Policy
ALLOWANCE_MODE=MAX              # Options: MAX (infinite), EXACT (specific amount)
VAULT_TRUSTED=false             # Set true for blue-chip protocols
REVOKE_ALLOWANCE_ON_EXIT=true   # Revoke allowances after withdrawal

# RPC Failover & Health
RPC_TIMEOUT_S=20                # RPC request timeout
RPC_MAX_RETRIES=2               # Max RPC retry attempts
MAX_BLOCK_STALENESS_S=90        # Max block age before switching RPC
```

#### Treasury Settings

```bash
# Treasury Configuration
TREASURY_ADDRESS=0x0000000000000000000000000000000000000000
TREASURY_AUTOMATION_ENABLED=false  # Enable automatic treasury payouts
TREASURY_TOKEN_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913  # USDC on Base
TREASURY_SWAP_API=https://base.api.0x.org/swap/v1/quote
```

#### Notifications

```bash
# Telegram Alerts
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHATID=your_chat_id
```

#### Token Addresses (Base Chain - Chain ID: 8453)

```bash
# Base Chain Tokens
WETH_TOKEN_ADDRESS=0x4200000000000000000000000000000000000006
USDC_BASE=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
USDBC_BASE=0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA
USDT_BASE=0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2
CBBTC_BASE=0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf
CBETH_BASE=0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22

# Protocol Addresses on Base
AAVE_POOL_ADDRESS_8453=0xA238Dd80C259a72e81d7e4664a9801593F98d1c5
AERODROME_ROUTER_8453=0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43
COMET_USDC_MARKET_BASE=0x46e6b214b524310239732D51387075E0e70970bf
```

See `.env.example` for complete list of token and protocol addresses across all supported chains.

### Configuration File (`bots/wave_rotation/config.json`)

```json
{
  "chains": ["base", "arbitrum", "polygon", "solana"],
  "min_tvl_usd": 100000,
  "delta_switch": 0.01,
  "reinvest_ratio": 0.5,
  "treasury_token": "USDC",
  "schedule_utc": "07:00",
  "stop_loss_daily": -0.10,
  "take_profit_daily": 0.05,
  "sources": {
    "defillama": true,
    "protocol_apis": ["aerodrome", "velodrome", "kamino"]
  },
  "adapters": {
    "pool:base:aave-v3:WETH": {
      "type": "aave_v3",
      "pool": "${AAVE_POOL_ADDRESS_8453}",
      "asset": "${WETH_TOKEN_ADDRESS}",
      "decimals": 18
    }
    // ... additional pool configurations
  }
}
```

## 🚀 Usage Guide

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/pietroscik/attuario-wallet.git
   cd attuario-wallet
   ```

2. **Set up Python virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r bots/wave_rotation/requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### First Run (Dry-Run Mode)

**Always test in dry-run mode first** to validate configuration without executing real transactions:

```bash
# Set dry-run mode in .env
export PORTFOLIO_DRY_RUN=true
export ONCHAIN_ENABLED=false
export DATA_SOURCE_MODE=PREFER_CACHE

# Run the strategy
cd attuario-wallet
source .venv/bin/activate
python3 bots/wave_rotation/strategy.py --print-status
```

### Example Output

```
=== Wave Rotation Status ===
Timestamp: 2025-10-30 11:18:18
Mode: DRY-RUN
Capital: 1.5 ETH
Current Pool: pool:base:aave-v3:WETH (Score: 0.0245)
Top Candidate: pool:base:morpho:USDC (Score: 0.0267, +8.9%)
Economic Edge: +0.032 ETH (~96 EUR) after gas
Action: SWITCH recommended (threshold met)
Treasury Balance: 0.45 ETH (~1,350 EUR)

============================================================
EXECUTION SUMMARY
============================================================
run_id=2025-10-30T13:45:22.123Z
timestamp=2025-10-30 13:45:22 UTC

FLAGS:
  DRY_RUN: False
  MULTI_STRATEGY: False

POOL:
  active_pool: base:aave-v3:usdc
  adapter: erc4626
  chain: base

AMOUNTS:
  amount_in: 1.234567 ETH
  amount_out: 1.235890 ETH

GAS:
  gas_used: 185,234
  gas_cost: 0.000234 ETH

PERFORMANCE:
  realized_pnl: +0.001323 ETH

TREASURY:
  treasury_move: YES
  treasury_amount: 0.000662 ETH
  reason: threshold_met

STATUS:
  errors: 0
  warnings: 0

============================================================
```

### Production Execution

Once validated in dry-run mode:

1. **Enable on-chain execution**:
   ```bash
   # In .env
   PORTFOLIO_DRY_RUN=false
   ONCHAIN_ENABLED=true
   PORTFOLIO_AUTOMATION_ENABLED=true
   ```

2. **Run via CI/CD entrypoint**:
   ```bash
   bash scripts/codex_entrypoint.sh
   ```

3. **Or run continuous loop**:
   ```bash
   bash scripts/run_wave_rotation_loop.sh
   ```

4. **Scheduled execution** (cron example):
   ```bash
   # Run daily at 7:00 UTC
   0 7 * * * cd /path/to/attuario-wallet && bash scripts/run_daily.sh
   ```

### State Management

The system maintains persistent state in `bots/wave_rotation/state.json`:

```json
{
  "current_pool": "pool:base:aave-v3:WETH",
  "capital_eth": 1.5,
  "last_move_at": "2025-10-30T07:00:00",
  "treasury_balance_eth": 0.45,
  "autopause_streak": 0,
  "daily_profit": 0.023
}
```

**Note**: `state.json` is gitignored and created automatically on first run.

## 🧪 Testing

### Test Suite

The project includes comprehensive tests for validating pool configurations, adapters, and core logic:

```bash
# Navigate to wave_rotation directory
cd bots/wave_rotation

# Run all tests
python3 test_basic.py          # Core functionality tests
python3 test_pools.py          # Pool configuration validation
python3 test_adapter_coverage.py  # Adapter integration tests
```

### Test Pool Configurations

```bash
# Validate pool configurations against environment
python3 bots/wave_rotation/validate_pools.py
```

Expected output:
```
✓ pool:base:aave-v3:WETH: type=aave_v3, asset configured
✓ pool:base:morpho:USDC: type=erc4626, asset configured
✓ pool:base:beefy:WETH-USDC: type=lp_beefy_aero, tokens configured
...
21/21 pools validated successfully
```

### Integration Tests

Integration tests use mock wallet data to validate the complete execution flow:

```bash
# Test with mock data (no real transactions)
export PORTFOLIO_DRY_RUN=true
python3 bots/wave_rotation/strategy.py --test-mode
```

### Adapter Validation

Validate that all configured adapters can be instantiated:

```bash
python3 bots/wave_rotation/validate_adapters.py
```

## 🛡️ Security & Safety

### Key Storage

**⚠️ CRITICAL**: Never commit private keys or sensitive credentials to version control.

- Store `PRIVATE_KEY` in `.env` (gitignored)
- Use hardware wallets or secure key management systems for production
- Consider using encrypted environment variable solutions (e.g., AWS Secrets Manager, HashiCorp Vault)

### Safe Deployment Practices

1. **Always start with dry-run mode**: Set `PORTFOLIO_DRY_RUN=true` for initial validation
2. **Test with small amounts**: Deploy minimal capital first to validate execution
3. **Monitor closely**: Use Telegram notifications and review logs regularly
4. **Review transactions**: Always verify on-chain transactions on block explorers
5. **Set conservative limits**: Configure `MIN_EDGE_ETH` and gas ceilings appropriately

### Risk Disclaimer

⚠️ **IMPORTANT**: This software manages real funds in DeFi protocols. Use at your own risk.

- **Smart contract risk**: All DeFi protocols carry smart contract vulnerabilities
- **Market risk**: Yields can change rapidly; losses are possible
- **Gas costs**: Ethereum/Base gas fees can be significant during network congestion
- **Impermanent loss**: LP positions may suffer from impermanent loss
- **Oracle risk**: Price feeds and yield data may be inaccurate or manipulated

**The developers are not responsible for any financial losses incurred through use of this software.**

### Security Audits

- Smart contracts: Consider professional audit before production deployment
- Bot logic: Review all adapter implementations before enabling
- Test thoroughly: Validate with small amounts in testnet/mainnet before scaling

## 📊 Project Structure

```
attuario-wallet/
├── .env.example                 # Environment variable template
├── .github/                     # GitHub workflows & CI/CD
│   └── SECRETS_SETUP.md         # Guide for GitHub secrets configuration
├── .gitignore                   # Git ignore rules
├── CODEX_RULES.md              # Core strategy rules & specifications
├── CODE_QUALITY_GUIDE.md       # Development standards
├── IMPLEMENTATION_SUMMARY.md   # Implementation details & pool summary
├── ASSET_INTEGRATION_GUIDE.md  # Guide for adding new assets
├── README.md                   # This file
├── analisi/                    # Analysis tools & scripts
├── bots/
│   └── wave_rotation/          # Main bot implementation
│       ├── strategy.py         # 🎯 Main entrypoint & orchestration
│       ├── portfolio.py        # Portfolio automation
│       ├── executor.py         # Execution logic
│       ├── scoring.py          # Scoring algorithm
│       ├── data_sources.py     # Yield data fetching
│       ├── selection_greedy.py # Pool selection & ranking
│       ├── treasury.py         # Treasury management
│       ├── onchain.py          # Web3 interactions
│       ├── ops_guard.py        # Operational safety checks
│       ├── logger.py           # Logging utilities
│       ├── adapters/           # Protocol adapters
│       │   ├── __init__.py     # Adapter registry
│       │   ├── aave_v3.py
│       │   ├── erc4626.py
│       │   ├── comet.py
│       │   ├── beefy_vault.py
│       │   ├── lp_beefy_aero.py
│       │   └── ...             # Additional adapters
│       ├── adapters_auto/      # Auto-detection & resolution
│       ├── utils/              # Utility modules
│       ├── config.json         # Pool configurations
│       ├── requirements.txt    # Python dependencies
│       ├── test_*.py           # Test files
│       ├── validate_*.py       # Validation scripts
│       └── README.md           # Bot-specific documentation
├── contracts/                  # Smart contracts (Hardhat)
│   ├── contracts/
│   │   └── AttuarioVault.sol   # Main vault contract
│   ├── scripts/                # Deployment scripts
│   ├── test/                   # Solidity tests
│   ├── hardhat.config.cts      # Hardhat configuration
│   └── package.json            # Node.js dependencies
├── scripts/
│   ├── codex_entrypoint.sh     # 🚀 CI/CD entrypoint
│   ├── run_daily.sh            # Daily execution script
│   ├── run_wave_rotation_loop.sh  # Continuous loop
│   ├── resolve_beefy_vaults.sh    # Beefy vault resolution
│   ├── resolve_yearn_vaults.sh    # Yearn vault resolution
│   └── ...                        # Additional utility scripts
└── tools/                      # Development tools
```

## 🧭 Roadmap / Future Enhancements

### Planned Features

- [x] Multi-protocol adapter system (20+ protocols)
- [x] Cross-chain support (Base, Arbitrum, Ethereum, Polygon, Solana, Aptos)
- [x] Economic edge calculation with gas optimization
- [x] Treasury automation with profit distribution
- [x] Autopause & risk management
- [ ] **Multi-Asset Portfolio**: Simultaneous allocation across multiple pools
- [ ] **LP Auto-Compounding**: Track and compound LP rewards automatically
- [ ] **Enhanced Optimizer**: Linear programming for optimal capital allocation
- [ ] **Treasury Diversification**: Multi-token treasury strategy
- [ ] **Advanced Risk Models**: Machine learning-based protocol risk scoring
- [ ] **Liquidation Protection**: Monitor health factors for lending positions
- [ ] **MEV Protection**: Flashbots integration for transaction privacy
- [ ] **Web Dashboard**: Real-time monitoring and manual controls
- [ ] **Backtesting Framework**: Historical strategy simulation

### Multi-Chain Expansion

Currently supported chains: **Base** (primary), Arbitrum, Ethereum, Polygon, Avalanche, Linea, BSC, Sonic, Solana, Aptos

Expansion targets:
- Optimism (Velodrome integration)
- zkSync Era
- Polygon zkEVM
- Scroll
- Mantle

### Protocol Integration Wishlist

- Curve Finance (stablecoin pools)
- Balancer v2 (weighted pools)
- GMX v2 (perpetual LP)
- Aura Finance (Balancer boosting)
- Convex Finance (Curve boosting)
- Pendle Finance (yield tokenization)
- Gains Network (GNS yield)

## 📜 License

This project is licensed under the **ISC License**. See `contracts/package.json` for details.

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow code quality standards in `CODE_QUALITY_GUIDE.md`
4. Add tests for new functionality
5. Ensure all tests pass
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/pietroscik/attuario-wallet/issues)
- **Documentation**: See `CODEX_RULES.md`, `IMPLEMENTATION_SUMMARY.md`, and `ASSET_INTEGRATION_GUIDE.md`
- **Examples**: Check `bots/wave_rotation/README.md` for detailed bot documentation

## ⚡ Quick Start Checklist

- [ ] Clone repository
- [ ] Install Python 3.10+ and dependencies
- [ ] Copy `.env.example` to `.env`
- [ ] Configure RPC endpoints and wallet address
- [ ] Set `PORTFOLIO_DRY_RUN=true` for testing
- [ ] Run `python3 bots/wave_rotation/strategy.py --print-status`
- [ ] Verify output and state.json creation
- [ ] Review logs and Telegram notifications (if configured)
- [ ] Gradually enable on-chain execution after validation

---

**Built with ❤️ for the DeFi community** | [GitHub](https://github.com/pietroscik/attuario-wallet)
