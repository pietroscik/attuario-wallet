#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Global constants for Attuario Wave Rotation strategy.

This module centralizes all magic numbers and configuration constants
to improve maintainability and reduce the risk of inconsistencies.
"""

from decimal import Decimal

# === Time Constants ===
SECONDS_PER_DAY = 86400
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24
DAYS_PER_YEAR = 365

# === Financial Constants ===
# Default exchange rate used for fallback calculations (EUR per ETH)
DEFAULT_FX_EUR_PER_ETH = Decimal("3000.0")

# Minimum treasury payout threshold (EUR)
DEFAULT_TREASURY_MIN_EUR = Decimal("0.5")

# Basis points per percentage point (100 bps = 1%)
BASIS_POINTS_PER_PERCENT = 100

# Basis points per unit (10000 bps = 100%)
BASIS_POINTS_PER_UNIT = 10000

# === Ethereum Constants ===
# Maximum uint256 value for unlimited approvals
MAX_UINT256 = (1 << 256) - 1

# Wei per Ether (10^18)
WEI_PER_ETHER = 10**18

# Gwei per Ether (10^9)
GWEI_PER_ETHER = 10**9

# Standard Ethereum address length (with 0x prefix)
ETH_ADDRESS_LENGTH = 42

# === Network Constants ===
# Base Chain ID (mainnet)
BASE_CHAIN_ID = 8453

# Base Testnet Chain ID
BASE_TESTNET_CHAIN_ID = 84532

# === API & Data Source Defaults ===
# Default timeout for HTTP requests (seconds)
DEFAULT_HTTP_TIMEOUT = 25

# Default cache TTL for API responses (seconds)
DEFAULT_CACHE_TTL = 300  # 5 minutes

# Maximum pools to scan from data sources
DEFAULT_MAX_POOLS_SCAN = 200

# === Transaction & Gas Defaults ===
# Default gas reserve for operations (ETH)
DEFAULT_GAS_RESERVE_ETH = Decimal("0.004")

# Minimum swap amount for treasury operations (ETH)
DEFAULT_MIN_TREASURY_SWAP_ETH = Decimal("0.0005")

# Default slippage tolerance for swaps (basis points)
DEFAULT_SLIPPAGE_BPS = 100  # 1%

# === Validation Limits ===
# Maximum allowed pool name length
MAX_POOL_NAME_LENGTH = 200

# Maximum allowed string length for logging
MAX_LOG_STRING_LENGTH = 1000

# Maximum reasonable APY for validation (%)
MAX_REASONABLE_APY_PERCENT = 10000  # 10000%

# Minimum reasonable APY for validation (%)
MIN_REASONABLE_APY_PERCENT = -100  # -100%

# === Scoring & Strategy Defaults ===
# Default operational cost baseline (as decimal, 5 basis points)
DEFAULT_OPERATIONAL_COST = 0.0005

# Default delta threshold for switching pools (as decimal, 1%)
DEFAULT_DELTA_SWITCH = 0.01

# Default reinvestment ratio (50%)
DEFAULT_REINVEST_RATIO = 0.5

# === Risk Constants ===
# Risk score bounds (0.0 = no risk, 1.0 = maximum risk)
MIN_RISK_SCORE = 0.0
MAX_RISK_SCORE = 1.0

# === Autopause Configuration ===
# Default crisis streak threshold before pause
DEFAULT_CRISIS_STREAK_THRESHOLD = 3

# Default resume wait time after pause (minutes)
DEFAULT_RESUME_WAIT_MINUTES = 360  # 6 hours

# Default cooldown between resume attempts (minutes)
DEFAULT_RESUME_COOLDOWN_MINUTES = 5

# === File & State Management ===
# Default capital scale for on-chain representation
DEFAULT_CAPITAL_SCALE = Decimal("1000000")

# === Protocol-Specific Constants ===
# Aave referral code (0 = no referral)
AAVE_NO_REFERRAL_CODE = 0

# === Logging & Monitoring ===
# Default log file name
DEFAULT_LOG_FILE = "daily.log"

# Default state file name
DEFAULT_STATE_FILE = "state.json"

# Default config file name
DEFAULT_CONFIG_FILE = "config.json"
