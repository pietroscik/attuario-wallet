#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pool validation script - checks that all required environment variables are set
and that the pool configurations are complete.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"


def load_config() -> Dict:
    """Load the configuration file."""
    with CONFIG_FILE.open() as fh:
        return json.load(fh)


def extract_env_vars(value) -> List[str]:
    """Extract environment variable names from a value."""
    if isinstance(value, str):
        # Find ${VAR_NAME} patterns
        import re
        matches = re.findall(r'\$\{([^}]+)\}', value)
        return matches
    elif isinstance(value, dict):
        vars_list = []
        for v in value.values():
            vars_list.extend(extract_env_vars(v))
        return vars_list
    elif isinstance(value, list):
        vars_list = []
        for v in value:
            vars_list.extend(extract_env_vars(v))
        return vars_list
    return []


def check_pool_env_vars(pool_id: str, adapter_config: Dict) -> Tuple[bool, List[str]]:
    """Check if all environment variables for a pool are set."""
    env_vars = extract_env_vars(adapter_config)
    missing = []
    
    for var in env_vars:
        if not os.getenv(var):
            missing.append(var)
    
    return len(missing) == 0, missing


def validate_pools():
    """Validate all pool configurations."""
    config = load_config()
    adapters = config.get("adapters", {})
    
    print("=" * 70)
    print("Pool Configuration Validation")
    print("=" * 70)
    print()
    
    total_pools = len(adapters)
    valid_pools = 0
    missing_env_vars = {}
    
    for pool_id, adapter_config in adapters.items():
        print(f"Checking: {pool_id}")
        print(f"  Type: {adapter_config.get('type', 'unknown')}")
        
        is_valid, missing = check_pool_env_vars(pool_id, adapter_config)
        
        if is_valid:
            print("  Status: ✓ Ready")
            valid_pools += 1
        else:
            print(f"  Status: ✗ Missing {len(missing)} environment variable(s)")
            missing_env_vars[pool_id] = missing
            for var in missing:
                print(f"    - {var}")
        print()
    
    print("=" * 70)
    print(f"Summary: {valid_pools}/{total_pools} pools ready")
    print("=" * 70)
    print()
    
    if missing_env_vars:
        print("Missing Environment Variables:")
        print("-" * 70)
        all_missing = set()
        for pool_id, vars_list in missing_env_vars.items():
            all_missing.update(vars_list)
        
        for var in sorted(all_missing):
            print(f"  {var}")
        print()
        print("Please set these variables in your .env file.")
        print("See .env.example for reference.")
        return False
    else:
        print("✅ All pools are properly configured!")
        return True


def show_pool_summary():
    """Show a summary of all configured pools."""
    config = load_config()
    adapters = config.get("adapters", {})
    
    # Group by type
    by_type = {}
    for pool_id, adapter_config in adapters.items():
        adapter_type = adapter_config.get("type", "unknown")
        if adapter_type not in by_type:
            by_type[adapter_type] = []
        by_type[adapter_type].append(pool_id)
    
    print()
    print("Pool Summary by Type:")
    print("-" * 70)
    for adapter_type, pools in sorted(by_type.items()):
        print(f"\n{adapter_type.upper()} ({len(pools)} pools):")
        for pool in pools:
            print(f"  • {pool}")
    print()


def main():
    """Main entry point."""
    try:
        # Try to load .env if available
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("Loaded .env file")
            print()
        except ImportError:
            print("Note: python-dotenv not installed, using system environment")
            print()
        
        show_pool_summary()
        is_valid = validate_pools()
        
        sys.exit(0 if is_valid else 1)
    
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
