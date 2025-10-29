# 🔧 Code Quality Improvements Guide

This document provides practical recommendations for improving code quality in the Attuario Wallet repository, based on the comprehensive audit conducted.

---

## 📋 Quick Wins (Immediate Implementation)

### 1. Use Structured Logging

**Replace** scattered `print()` statements **with** the new logging module:

```python
# Before (❌)
print(f"[data] GET {url} failed: {exc}")

# After (✅)
from logging_config import get_logger

logger = get_logger(__name__)
logger.error("Data fetch failed", extra={"url": url, "error": str(exc)})
```

**Benefits**:
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Structured output for log aggregation tools
- Better filtering and searching capabilities
- Consistent formatting across the codebase

---

### 2. Import Constants Instead of Magic Numbers

```python
# Before (❌)
return annual_cost / 365.0

# After (✅)
from constants import DAYS_PER_YEAR

return annual_cost / DAYS_PER_YEAR
```

**Benefits**:
- Single source of truth for values
- Easier to update and maintain
- Self-documenting code

---

### 3. Add Type Hints Consistently

```python
# Before (❌)
def _auto_adapter(pool_id, address, signer, w3):
    ...

# After (✅)
from eth_account.signers.local import LocalAccount
from web3 import Web3

def _auto_adapter(
    pool_id: str,
    address: str | None,
    signer: LocalAccount,
    w3: Web3,
) -> tuple[Adapter | None, str]:
    ...
```

**Benefits**:
- Better IDE support and autocomplete
- Early error detection
- Self-documenting function signatures

---

### 4. Use Early Returns to Reduce Nesting

```python
# Before (❌)
def process_pool(pool):
    if pool is not None:
        if pool.get("tvl") > 1000:
            if pool.get("apy") > 0:
                return calculate_score(pool)
    return 0.0

# After (✅)
def process_pool(pool):
    if pool is None:
        return 0.0
    if pool.get("tvl", 0) <= 1000:
        return 0.0
    if pool.get("apy", 0) <= 0:
        return 0.0
    
    return calculate_score(pool)
```

**Benefits**:
- Flatter code structure
- Easier to follow logic
- Reduced cognitive load

---

## 🏗️ Medium-Term Improvements

### 5. Extract Base Adapter Class

Create a common base class for all adapters to reduce duplication:

```python
# New file: bots/wave_rotation/adapters/base_impl.py

from abc import ABC, abstractmethod
from typing import Dict, Optional
from web3 import Web3

class BaseAdapter(ABC):
    """Base implementation with common transaction utilities."""
    
    def __init__(self, w3: Web3, signer, sender: str):
        self.w3 = w3
        self.signer = signer
        self.sender = Web3.to_checksum_address(sender)
    
    def _get_nonce(self) -> int:
        """Get current nonce for sender."""
        return self.w3.eth.get_transaction_count(self.sender)
    
    def _estimate_gas(self, tx: Dict) -> int:
        """Estimate gas for transaction."""
        return self.w3.eth.estimate_gas(tx)
    
    def _sign_and_send(
        self,
        tx: Dict,
        *,
        nonce: Optional[int] = None,
        dry_run: bool = True
    ) -> str:
        """Sign and send transaction with optional dry run."""
        tx.setdefault("chainId", self.w3.eth.chain_id)
        tx.setdefault("from", self.sender)
        
        if nonce is None:
            nonce = self._get_nonce()
        tx["nonce"] = nonce
        
        if "gas" not in tx:
            tx["gas"] = self._estimate_gas(tx)
        
        # Set gas prices
        gas_price = self.w3.eth.gas_price
        tx.setdefault("maxFeePerGas", gas_price)
        tx.setdefault("maxPriorityFeePerGas", gas_price)
        
        # Dry simulation (optional)
        if dry_run:
            call_tx = {k: tx[k] for k in ("to", "from", "data") if k in tx}
            call_tx["value"] = tx.get("value", 0)
            self.w3.eth.call(call_tx)
        
        # Sign and send
        signed = self.signer.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()
    
    @abstractmethod
    def deposit_all(self) -> Dict[str, object]:
        """Deposit all available assets."""
        pass
    
    @abstractmethod
    def withdraw_all(self) -> Dict[str, object]:
        """Withdraw all deposited assets."""
        pass
```

**Benefits**:
- Reduce 200-300 lines of duplicate code
- Consistent transaction handling
- Easier to add new features (e.g., gas optimization)
- Better testability

---

### 6. Refactor Long Functions

Break down the 482-line `main()` function:

```python
# strategy.py - Refactored structure

def initialize_strategy() -> tuple[StrategyConfig, StrategyState]:
    """Load configuration and state."""
    cfg = StrategyConfig.load(CONFIG_FILE)
    state = StrategyState.load(STATE_FILE)
    return cfg, state


def check_autopause_conditions(state: StrategyState, cfg: StrategyConfig) -> bool:
    """Determine if strategy should be paused."""
    if state.crisis_streak >= cfg.autopause.get("streak", 3):
        return True
    return False


def evaluate_portfolio(
    cfg: StrategyConfig,
    state: StrategyState,
    pools: list[dict]
) -> dict | None:
    """Select best pool based on scoring."""
    # Pool evaluation logic
    ...


def execute_rebalance(
    best_pool: dict,
    current_pool: dict | None,
    capital: float
) -> bool:
    """Move capital to new pool if needed."""
    # Rebalancing logic
    ...


def finalize_strategy(state: StrategyState, results: dict) -> None:
    """Save state and send reports."""
    state.save(STATE_FILE)
    send_telegram_report(results)


def main() -> None:
    """Main strategy execution (orchestrator)."""
    cfg, state = initialize_strategy()
    
    if check_autopause_conditions(state, cfg):
        handle_pause_logic(state, cfg)
        return
    
    pools = fetch_pools_scoped(cfg)
    best_pool = evaluate_portfolio(cfg, state, pools)
    
    if best_pool:
        success = execute_rebalance(best_pool, state.pool_id, capital)
        finalize_strategy(state, {"success": success, "pool": best_pool})
```

**Benefits**:
- Each function has single responsibility
- Easier to test individual components
- Better code navigation
- Improved maintainability

---

### 7. Add Comprehensive Docstrings

Follow Google docstring style:

```python
def normalized_score(pool: dict, *, adapter_src: str = "", cfg: Any | None = None) -> float:
    """Calculate normalized pool score using the CODEX formula.
    
    The score is computed as:
        score = daily_rate / (1 + daily_cost * (1 - risk_score))
    
    where:
        - daily_rate: Daily compounded return from APY
        - daily_cost: Daily operational costs
        - risk_score: Risk factor (0.0 = safe, 1.0 = risky)
    
    Args:
        pool: Pool data dictionary containing 'apy', 'fee_pct', and 'risk_score'
        adapter_src: Source of adapter (legacy parameter, unused)
        cfg: Configuration object (legacy parameter, unused)
    
    Returns:
        Normalized score as a float. Returns 0 or negative for invalid/unprofitable pools.
    
    Examples:
        >>> pool = {"apy": 0.05, "fee_pct": 0.001, "risk_score": 0.2}
        >>> score = normalized_score(pool)
        >>> print(f"Score: {score:.6f}")
        Score: 0.000133
    
    Note:
        The function implements the scoring algorithm defined in CODEX_RULES.
    """
    # Implementation...
```

**Benefits**:
- Clear documentation for users
- Examples make usage obvious
- IDE tooltips show full context
- Better onboarding for new developers

---

## 🚀 Long-Term Architectural Improvements

### 8. Unified State Management with SQLite

Replace scattered state files with a database:

```python
# state_manager.py

import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

class StateManager:
    """Centralized state management with SQLite."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS capital_history (
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    amount REAL,
                    pool_id TEXT,
                    operation TEXT
                )
            """)
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with automatic commit/rollback."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_state(self, key: str) -> Optional[str]:
        """Get state value by key."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT value FROM strategy_state WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
    
    def set_state(self, key: str, value: str) -> None:
        """Set state value with automatic timestamp."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO strategy_state (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, value)
            )
    
    def snapshot(self) -> dict:
        """Create full state snapshot for rollback."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT key, value FROM strategy_state")
            return dict(cursor.fetchall())
    
    def restore(self, snapshot: dict) -> None:
        """Restore state from snapshot."""
        with self._get_connection() as conn:
            for key, value in snapshot.items():
                conn.execute(
                    "INSERT OR REPLACE INTO strategy_state (key, value) VALUES (?, ?)",
                    (key, value)
                )
```

**Benefits**:
- ACID transactions
- State history and audit trail
- Snapshot and rollback capability
- Query flexibility
- Better data integrity

---

### 9. Implement Health Checks

Add monitoring for production deployments:

```python
# health_check.py

from datetime import datetime, timedelta
from pathlib import Path
import json

class HealthChecker:
    """Monitor strategy health and alert on issues."""
    
    def __init__(self, state_file: Path):
        self.state_file = state_file
    
    def check_last_run(self, max_age_minutes: int = 30) -> dict:
        """Check if strategy ran recently."""
        if not self.state_file.exists():
            return {
                "healthy": False,
                "reason": "state_file_missing"
            }
        
        try:
            with open(self.state_file) as f:
                state = json.load(f)
            
            last_update = state.get("updated_at")
            if not last_update:
                return {
                    "healthy": False,
                    "reason": "no_timestamp"
                }
            
            last_dt = datetime.fromisoformat(last_update)
            age = datetime.utcnow() - last_dt
            
            if age > timedelta(minutes=max_age_minutes):
                return {
                    "healthy": False,
                    "reason": "stale_state",
                    "age_minutes": age.total_seconds() / 60
                }
            
            return {
                "healthy": True,
                "last_run": last_update,
                "age_minutes": age.total_seconds() / 60
            }
        except Exception as e:
            return {
                "healthy": False,
                "reason": "check_failed",
                "error": str(e)
            }
    
    def check_capital_sanity(self, state_file: Path) -> dict:
        """Verify capital values are reasonable."""
        # Implementation...
        pass
    
    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        # Implementation...
        pass
```

---

## 📊 Testing Recommendations

### 10. Add Unit Tests for Critical Functions

```python
# tests/test_scoring.py

import pytest
from scoring import daily_rate, normalized_score

class TestDailyRate:
    def test_positive_apy(self):
        """Test daily rate calculation with positive APY."""
        apy = 0.05  # 5% APY
        daily = daily_rate(apy)
        
        # Check it's a small positive number
        assert 0 < daily < 0.001
        
        # Verify compound formula: (1 + daily)^365 ≈ 1.05
        annual = (1 + daily) ** 365
        assert abs(annual - 1.05) < 0.0001
    
    def test_negative_apy(self):
        """Test that extreme negative APY returns 0."""
        assert daily_rate(-1.0) == 0.0
        assert daily_rate(-0.99) == 0.0
    
    def test_zero_apy(self):
        """Test zero APY returns zero daily rate."""
        assert daily_rate(0.0) == 0.0
    
    def test_invalid_input(self):
        """Test invalid inputs return 0."""
        assert daily_rate(None) == 0.0
        assert daily_rate("invalid") == 0.0


class TestNormalizedScore:
    def test_basic_score(self):
        """Test basic score calculation."""
        pool = {
            "apy": 0.05,
            "fee_pct": 0.001,
            "risk_score": 0.2
        }
        score = normalized_score(pool)
        assert score > 0
        assert isinstance(score, float)
    
    def test_zero_apy_returns_zero(self):
        """Test that zero APY results in zero score."""
        pool = {"apy": 0.0, "fee_pct": 0.0, "risk_score": 0.0}
        assert normalized_score(pool) == 0.0
    
    def test_high_cost_reduces_score(self):
        """Test that higher costs reduce score."""
        pool_low_cost = {"apy": 0.05, "fee_pct": 0.001, "risk_score": 0.0}
        pool_high_cost = {"apy": 0.05, "fee_pct": 0.01, "risk_score": 0.0}
        
        assert normalized_score(pool_low_cost) > normalized_score(pool_high_cost)
```

---

## ✅ Implementation Checklist

Use this checklist to track implementation progress:

### Immediate (Week 1)
- [ ] Replace print() with logging_config in all modules
- [ ] Add input validation to remaining blockchain functions
- [ ] Update all modules to use constants.py
- [ ] Run and fix any linting errors

### Short-term (Month 1)
- [ ] Create BaseAdapter class and migrate existing adapters
- [ ] Refactor strategy.py main() function
- [ ] Add docstrings to public functions (target: 80% coverage)
- [ ] Add unit tests for scoring and validation modules
- [ ] Implement health check system

### Long-term (Quarter 1)
- [ ] Migrate to SQLite state management
- [ ] Add Prometheus metrics export
- [ ] Implement adapter capability discovery
- [ ] Create integration tests
- [ ] Set up CI/CD test pipeline

---

## 📚 Additional Resources

- **Python Type Hints**: https://docs.python.org/3/library/typing.html
- **Google Python Style Guide**: https://google.github.io/styleguide/pyguide.html
- **Clean Code Principles**: https://gist.github.com/wojteklu/73c6914cc446146b8b533c0988cf8d29
- **SQLite Best Practices**: https://www.sqlite.org/bestpractice.html
- **Prometheus Python Client**: https://github.com/prometheus/client_python

---

**Last Updated**: 2025-10-29  
**Document Maintainer**: GitHub Copilot Code Review Agent
