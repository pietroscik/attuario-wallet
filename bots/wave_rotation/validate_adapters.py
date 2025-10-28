#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Validate all adapter configurations and environment variables."""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config() -> Dict:
    """Load configuration from config.json."""
    with CONFIG_PATH.open() as f:
        return json.load(f)


def substitute_env_vars(value: str) -> str:
    """Substitute ${VAR_NAME} with environment variable values."""
    if not isinstance(value, str):
        return value
    
    import re
    pattern = r'\$\{([^}]+)\}'
    
    def replace(match):
        var_name = match.group(1)
        return os.getenv(var_name, f"${{{var_name}}}")
    
    return re.sub(pattern, replace, value)


def validate_adapters(config: Dict) -> Dict[str, List[str]]:
    """Validate all adapter configurations."""
    adapters = config.get("adapters", {})
    
    results = {
        "valid": [],
        "invalid": [],
        "missing_vars": [],
    }
    
    adapter_types = {}
    
    for pool_id, adapter_config in adapters.items():
        adapter_type = adapter_config.get("type", "unknown")
        
        if adapter_type not in adapter_types:
            adapter_types[adapter_type] = 0
        adapter_types[adapter_type] += 1
        
        # Check required fields based on adapter type
        missing_fields = []
        has_missing_env = False
        
        if adapter_type == "aave_v3":
            for field in ["pool", "asset"]:
                value = substitute_env_vars(adapter_config.get(field, ""))
                if not value or value.startswith("${"):
                    missing_fields.append(field)
                    has_missing_env = True
                    
        elif adapter_type == "lp_beefy_aero":
            for field in ["router", "beefy_vault", "token0", "token1"]:
                value = substitute_env_vars(adapter_config.get(field, ""))
                if not value or value.startswith("${"):
                    missing_fields.append(field)
                    has_missing_env = True
                    
        elif adapter_type == "erc4626":
            for field in ["vault", "asset"]:
                value = substitute_env_vars(adapter_config.get(field, ""))
                if not value or value.startswith("${"):
                    missing_fields.append(field)
                    has_missing_env = True
                    
        elif adapter_type == "yearn":
            for field in ["vault", "asset"]:
                value = substitute_env_vars(adapter_config.get(field, ""))
                if not value or value.startswith("${"):
                    missing_fields.append(field)
                    has_missing_env = True
                    
        elif adapter_type == "comet":
            for field in ["market", "asset"]:
                value = substitute_env_vars(adapter_config.get(field, ""))
                if not value or value.startswith("${"):
                    missing_fields.append(field)
                    has_missing_env = True
                    
        elif adapter_type == "ctoken":
            for field in ["ctoken", "asset"]:
                value = substitute_env_vars(adapter_config.get(field, ""))
                if not value or value.startswith("${"):
                    missing_fields.append(field)
                    has_missing_env = True
        
        if missing_fields:
            results["missing_vars"].append(f"{pool_id} ({adapter_type}): {', '.join(missing_fields)}")
        elif has_missing_env:
            results["invalid"].append(f"{pool_id} ({adapter_type})")
        else:
            results["valid"].append(f"{pool_id} ({adapter_type})")
    
    return results, adapter_types


def main():
    """Main validation function."""
    print("=" * 80)
    print("ADAPTER CONFIGURATION VALIDATOR")
    print("=" * 80)
    print()
    
    config = load_config()
    results, adapter_types = validate_adapters(config)
    
    print("📊 ADAPTER SUMMARY BY TYPE:")
    print("-" * 80)
    for adapter_type, count in sorted(adapter_types.items()):
        print(f"  {adapter_type.upper()}: {count} pools")
    print()
    
    total_pools = len(config.get("adapters", {}))
    valid_count = len(results["valid"])
    invalid_count = len(results["invalid"])
    missing_count = len(results["missing_vars"])
    
    print(f"📋 VALIDATION RESULTS:")
    print("-" * 80)
    print(f"  Total pools configured: {total_pools}")
    print(f"  ✅ Valid (all env vars set): {valid_count}")
    print(f"  ⚠️  Invalid (missing env vars): {invalid_count}")
    print(f"  ❌ Missing required fields: {missing_count}")
    print()
    
    if results["valid"]:
        print("✅ VALID POOLS (ready to use):")
        print("-" * 80)
        for pool in results["valid"]:
            print(f"  • {pool}")
        print()
    
    if results["missing_vars"]:
        print("❌ POOLS WITH MISSING ENVIRONMENT VARIABLES:")
        print("-" * 80)
        for pool in results["missing_vars"]:
            print(f"  • {pool}")
        print()
    
    if results["invalid"]:
        print("⚠️  POOLS WITH INCOMPLETE CONFIGURATION:")
        print("-" * 80)
        for pool in results["invalid"]:
            print(f"  • {pool}")
        print()
    
    print("=" * 80)
    print("💡 TIP: Set missing environment variables in .env file")
    print("   or use the resolution scripts in scripts/ directory:")
    print("   - scripts/resolve_beefy_vaults.sh")
    print("   - scripts/resolve_yearn_vaults.sh")
    print("   - scripts/resolve_compound_markets.sh")
    print("   - scripts/resolve_erc4626_vaults.sh")
    print("=" * 80)
    print()
    
    # Exit with appropriate code
    if missing_count > 0 or invalid_count == total_pools:
        print("❌ Validation failed: Critical issues found")
        sys.exit(1)
    elif invalid_count > 0:
        print("⚠️  Validation passed with warnings")
        sys.exit(0)
    else:
        print("✅ All adapter configurations are valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()
