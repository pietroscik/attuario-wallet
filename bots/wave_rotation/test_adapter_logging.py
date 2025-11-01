#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test adapter registry logging for error conditions."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from adapters import get_adapter


def test_no_adapter_logging():
    """Test that no_adapter error produces clear logging."""
    print("\n🧪 Testing no_adapter logging...")
    
    config: Dict[str, object] = {
        "adapters": {
            "pool:base:aave-v3:USDC": {
                "type": "aave_v3",
                "pool": "0x123",
                "asset": "0x456"
            }
        }
    }
    
    # Mock w3 and account
    w3 = MagicMock()
    account = MagicMock()
    account.address = "0xTest"
    
    # Capture stdout
    captured_output = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured_output
    
    # Try to get adapter for non-existent pool
    adapter, error = get_adapter("pool:nonexistent:pool", config, w3, account)
    
    # Restore stdout
    sys.stdout = old_stdout
    output = captured_output.getvalue()
    
    # Verify error is returned
    assert adapter is None, "Adapter should be None"
    assert error == "no_adapter:pool:nonexistent:pool", f"Expected no_adapter error, got: {error}"
    
    # Verify logging message
    assert "no_adapter" in output, "Output should contain 'no_adapter'"
    assert "pool:nonexistent:pool" in output, "Output should contain pool_id"
    assert "not found in config.json" in output, "Output should explain the error"
    
    print("✅ no_adapter logging test passed")


def test_unknown_type_logging():
    """Test that unknown_type error produces clear logging."""
    print("\n🧪 Testing unknown_type logging...")
    
    config: Dict[str, object] = {
        "adapters": {
            "pool:test:invalid": {
                "type": "invalid_adapter_type",
                "vault": "0x123"
            }
        }
    }
    
    # Mock w3 and account
    w3 = MagicMock()
    account = MagicMock()
    account.address = "0xTest"
    
    # Capture stdout
    captured_output = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured_output
    
    # Try to get adapter with invalid type
    adapter, error = get_adapter("pool:test:invalid", config, w3, account)
    
    # Restore stdout
    sys.stdout = old_stdout
    output = captured_output.getvalue()
    
    # Verify error is returned
    assert adapter is None, "Adapter should be None"
    assert error == "unknown_type:invalid_adapter_type", f"Expected unknown_type error, got: {error}"
    
    # Verify logging message
    assert "unknown_type" in output, "Output should contain 'unknown_type'"
    assert "pool:test:invalid" in output, "Output should contain pool_id"
    assert "invalid_adapter_type" in output, "Output should contain the invalid type"
    assert "Available types:" in output, "Output should list available types"
    
    print("✅ unknown_type logging test passed")


def test_pool_key_resolution():
    """Test that pool key resolution works with and without 'pool:' prefix."""
    print("\n🧪 Testing pool key resolution...")
    
    config: Dict[str, object] = {
        "adapters": {
            "pool:base:aave-v3:USDC": {
                "type": "aave_v3",
                "pool": "0x123",
                "asset": "0x456"
            }
        }
    }
    
    # Mock w3 and account
    w3 = MagicMock()
    account = MagicMock()
    account.address = "0xTest"
    
    # Capture stdout to suppress error messages from this test
    captured_output = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured_output
    
    try:
        # Test with full key (should find it)
        adapter1, error1 = get_adapter("pool:base:aave-v3:USDC", config, w3, account)
        
        # Test with bare key (should also find it with pool: prefix)
        adapter2, error2 = get_adapter("base:aave-v3:USDC", config, w3, account)
    finally:
        # Restore stdout
        sys.stdout = old_stdout
    
    # Note: Both will return errors because we can't actually instantiate adapters
    # without proper w3 connection, but the error should NOT be "no_adapter"
    assert not error1 or not error1.startswith("no_adapter:"), \
        f"Full key should be found (error: {error1})"
    assert not error2 or not error2.startswith("no_adapter:"), \
        f"Bare key should be resolved to pool: prefix (error: {error2})"
    
    print("✅ Pool key resolution test passed")


def test_adapter_with_unset_type():
    """Test that missing type field is handled."""
    print("\n🧪 Testing adapter with unset type...")
    
    config: Dict[str, object] = {
        "adapters": {
            "pool:test:notype": {
                "vault": "0x123"
                # Note: no "type" field
            }
        }
    }
    
    # Mock w3 and account
    w3 = MagicMock()
    account = MagicMock()
    account.address = "0xTest"
    
    # Capture stdout
    captured_output = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured_output
    
    # Try to get adapter with missing type
    adapter, error = get_adapter("pool:test:notype", config, w3, account)
    
    # Restore stdout
    sys.stdout = old_stdout
    output = captured_output.getvalue()
    
    # Verify error is returned
    assert adapter is None, "Adapter should be None"
    assert error == "unknown_type:unset", f"Expected unknown_type:unset error, got: {error}"
    
    # Verify logging message
    assert "unknown_type" in output, "Output should contain 'unknown_type'"
    assert "unset" in output, "Output should indicate type is unset"
    
    print("✅ Adapter with unset type test passed")


def main():
    """Run all adapter logging tests."""
    print("=" * 80)
    print("ADAPTER LOGGING TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_no_adapter_logging,
        test_unknown_type_logging,
        test_pool_key_resolution,
        test_adapter_with_unset_type,
    ]
    
    failed = []
    
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed.append(test.__name__)
        except Exception as e:
            print(f"❌ {test.__name__} error: {e}")
            failed.append(test.__name__)
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    if failed:
        print(f"❌ {len(failed)}/{len(tests)} tests failed:")
        for name in failed:
            print(f"  - {name}")
        return 1
    else:
        print(f"✅ All {len(tests)} tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
