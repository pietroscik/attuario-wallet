#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Standalone tests for security modules (no pytest required).

Run: python test_security_modules.py
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_run_lock():
    """Test run-lock mechanism."""
    print("Testing run-lock...")
    
    from run_lock import RunLock, RunLockError, LOCK_FILE
    
    # Use temp file for testing
    test_lock = Path(tempfile.gettempdir()) / f"test_run_lock_{os.getpid()}"
    
    # Test acquiring lock
    lock1 = RunLock(timeout_seconds=2)
    lock1.lock_file = test_lock
    
    try:
        with lock1:
            assert lock1.acquired, "Lock should be acquired"
            assert test_lock.exists(), "Lock file should exist"
            
            # Try to acquire again (should fail)
            lock2 = RunLock(timeout_seconds=2)
            lock2.lock_file = test_lock
            
            try:
                with lock2:
                    assert False, "Should not acquire lock twice"
            except RunLockError as exc:
                assert "in progress" in str(exc).lower(), f"Expected 'in progress' in error: {exc}"
                print("  ✓ Concurrent lock correctly prevented")
        
        # After exiting context, lock should be released
        assert not test_lock.exists(), "Lock file should be cleaned up"
        print("  ✓ Lock cleanup successful")
        
    finally:
        # Cleanup
        if test_lock.exists():
            test_lock.unlink()
    
    # Test stale lock detection
    old_time = time.time() - 7200  # 2 hours ago
    test_lock.write_text(f"9999\n{old_time}\n")
    # Set file mtime to old time
    os.utime(test_lock, (old_time, old_time))
    
    lock3 = RunLock(timeout_seconds=1800)  # 30 minute timeout (less than lock age)
    lock3.lock_file = test_lock
    
    try:
        with lock3:
            assert lock3.acquired, "Should acquire stale lock"
            print("  ✓ Stale lock removal works")
    finally:
        if test_lock.exists():
            test_lock.unlink()
    
    print("✓ Run-lock tests passed\n")


def test_tx_errors():
    """Test transaction error classification."""
    print("Testing transaction error classification...")
    
    from tx_errors import (
        classify_error,
        NonceError,
        GasError,
        SlippageError,
        PausedError,
        decode_revert_reason,
    )
    
    # Test nonce error
    error1 = classify_error("nonce too low")
    assert isinstance(error1, NonceError), f"Expected NonceError, got {type(error1)}"
    print("  ✓ Nonce error classified")
    
    # Test gas error
    error2 = classify_error("insufficient funds for gas")
    assert isinstance(error2, GasError), f"Expected GasError, got {type(error2)}"
    print("  ✓ Gas error classified")
    
    # Test slippage error
    error3 = classify_error("slippage exceeded")
    assert isinstance(error3, SlippageError), f"Expected SlippageError, got {type(error3)}"
    print("  ✓ Slippage error classified")
    
    # Test paused error
    error4 = classify_error("contract paused")
    assert isinstance(error4, PausedError), f"Expected PausedError, got {type(error4)}"
    print("  ✓ Paused error classified")
    
    print("✓ Transaction error tests passed\n")


def test_kill_switch():
    """Test kill-switch mechanism."""
    print("Testing kill-switch...")
    
    from kill_switch import KillSwitch
    
    test_file = Path(tempfile.gettempdir()) / f"test_kill_switch_{os.getpid()}"
    
    try:
        # Test normal operation
        ks = KillSwitch(threshold=3, state_file=test_file)
        ks.check()  # Should not raise
        print("  ✓ Initial check passed")
        
        # Record errors
        ks.record_error("Error 1")
        assert ks.state.consecutive_errors == 1, "Should have 1 error"
        print("  ✓ Error recording works")
        
        ks.record_error("Error 2")
        assert ks.state.consecutive_errors == 2, "Should have 2 errors"
        
        ks.record_error("Error 3")
        assert ks.state.consecutive_errors == 3, "Should have 3 errors"
        assert ks.state.triggered, "Kill-switch should be triggered"
        print("  ✓ Kill-switch triggered after threshold")
        
        # Check should now raise
        try:
            ks.check()
            assert False, "Check should raise after trigger"
        except RuntimeError as exc:
            assert "Kill-switch triggered" in str(exc), f"Expected trigger message: {exc}"
            print("  ✓ Triggered check raises correctly")
        
        # Test reset
        ks.reset()
        assert ks.state.consecutive_errors == 0, "Should be reset"
        assert not ks.state.triggered, "Should not be triggered"
        ks.check()  # Should not raise
        print("  ✓ Reset works")
        
        # Test success recording
        ks.record_error("Error 1")
        ks.record_success()
        assert ks.state.consecutive_errors == 0, "Should reset on success"
        print("  ✓ Success recording resets counter")
        
    finally:
        if test_file.exists():
            test_file.unlink()
    
    print("✓ Kill-switch tests passed\n")


def test_slippage():
    """Test slippage protection."""
    print("Testing slippage protection...")
    
    from slippage import calculate_min_amount_out, validate_slippage, get_price_impact_bps
    
    # Test min amount calculation
    expected = 1000000  # 1M units
    min_out = calculate_min_amount_out(expected, slippage_bps=100)  # 1%
    assert min_out == 990000, f"Expected 990000, got {min_out}"
    print("  ✓ Min amount calculation correct")
    
    # Test validation
    assert validate_slippage(expected, 990001, slippage_bps=100), "Should pass validation"
    assert not validate_slippage(expected, 989999, slippage_bps=100), "Should fail validation"
    print("  ✓ Slippage validation works")
    
    # Test price impact
    impact = get_price_impact_bps(1000, 990, 1.0)
    assert impact == 100, f"Expected 100 bps impact, got {impact}"
    print("  ✓ Price impact calculation correct")
    
    print("✓ Slippage tests passed\n")


def test_safe_math():
    """Test safe math utilities."""
    print("Testing safe math...")
    
    from safe_math import safe_decimals, safe_amount, clamp_to_balance, format_amount
    
    # Test decimals validation
    assert safe_decimals(18) == 18, "Valid decimals should pass"
    assert safe_decimals(-1, default=18) == 18, "Negative should use default"
    assert safe_decimals(100, default=18) == 18, "Too large should use default"
    print("  ✓ Decimal validation works")
    
    # Test amount conversion
    amount = safe_amount(1.5, decimals=18)
    assert amount == 1500000000000000000, f"Expected 1.5 ETH in wei, got {amount}"
    print("  ✓ Amount conversion works")
    
    # Test clamping
    clamped = clamp_to_balance(2.0, balance=1500000000000000000, decimals=18)
    assert clamped == 1500000000000000000, f"Should clamp to balance, got {clamped}"
    print("  ✓ Balance clamping works")
    
    # Test formatting
    formatted = format_amount(1500000000000000000, decimals=18, precision=2)
    assert "1.5" in formatted, f"Expected 1.5 in formatted output: {formatted}"
    print("  ✓ Amount formatting works")
    
    print("✓ Safe math tests passed\n")


def test_execution_summary():
    """Test execution summary."""
    print("Testing execution summary...")
    
    from execution_summary import create_execution_summary
    
    summary = create_execution_summary(dry_run=False, multi_strategy=False)
    
    assert summary.dry_run == False, "Dry run flag should be False"
    assert summary.multi_strategy == False, "Multi strategy flag should be False"
    assert summary.errors == 0, "Initial errors should be 0"
    print("  ✓ Summary creation works")
    
    # Test adding errors/warnings
    summary.add_error("Test error")
    assert summary.errors == 1, "Should have 1 error"
    assert len(summary.error_messages) == 1, "Should have 1 error message"
    
    summary.add_warning("Test warning")
    assert summary.warnings == 1, "Should have 1 warning"
    print("  ✓ Error/warning tracking works")
    
    # Test formatting
    text = summary.format_text()
    assert "EXECUTION SUMMARY" in text, "Should have header"
    assert "errors: 1" in text, "Should show error count"
    assert "warnings: 1" in text, "Should show warning count"
    print("  ✓ Text formatting works")
    
    # Test JSON
    json_str = summary.to_json()
    assert "run_id" in json_str, "JSON should have run_id"
    print("  ✓ JSON serialization works")
    
    print("✓ Execution summary tests passed\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Running Security Module Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_run_lock,
        test_tx_errors,
        test_kill_switch,
        test_slippage,
        test_safe_math,
        test_execution_summary,
    ]
    
    failed = []
    for test_func in tests:
        try:
            test_func()
        except Exception as exc:
            print(f"✗ {test_func.__name__} FAILED: {exc}\n")
            import traceback
            traceback.print_exc()
            failed.append(test_func.__name__)
    
    print("=" * 60)
    if failed:
        print(f"FAILED: {len(failed)} test(s)")
        for name in failed:
            print(f"  - {name}")
        return 1
    else:
        print("SUCCESS: All tests passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
