# Auto-Resolution of Beefy Vault Addresses

This document explains how Beefy vault addresses are automatically resolved from the Beefy Finance API.

## Overview

The `scripts/resolve_beefy_vaults.sh` script automatically fetches current Beefy vault addresses from the Beefy Finance API for Base chain pools. This eliminates the need to manually find and configure vault addresses.

## How It Works

### 1. Beefy API Query

The script queries `https://api.beefy.finance/vaults` to get all available vaults across all chains.

### 2. Filtering

For each pool, the script applies these filters:
- **Chain**: Only Base network (`chain=="base"`)
- **Status**: Active vaults only (excludes EOL/deprecated)
- **Platform**: Aerodrome or related platforms
- **Assets**: Matches the token pair (e.g., "USDC-USDT")

### 3. Variable Setting

Found addresses are set in two places:
- **`$GITHUB_ENV`**: Available immediately in the current workflow run
- **GitHub Environment Variables**: Persisted for future runs (requires permissions)

## Pools Resolved

The script resolves these Beefy vault addresses:

| Pool Pair | Environment Variable | Purpose |
|-----------|---------------------|---------|
| USDC-USDT | `BEEFY_USDC_USDT_VAULT` | Stable/stable pair |
| WETH-USDC | `BEEFY_WETH_USDC_VAULT` | ETH/stable pair |
| WETH-USDT | `BEEFY_WETH_USDT_VAULT` | ETH/stable pair |
| cbETH-WETH | `BEEFY_CBETH_WETH_VAULT` | LST pair |

## GitHub Actions Integration

### Workflow Steps

The workflow includes these steps in order:

```yaml
- name: Setup tools
  run: sudo apt-get update && sudo apt-get install -y jq

- name: Resolve Beefy vaults (Base)
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    ENV_NAME: copilot
  run: |
    scripts/resolve_beefy_vaults.sh
    echo "Beefy vaults (runtime):"
    env | grep -E '^BEEFY_.*_VAULT=' || true
```

### Requirements

- **jq**: JSON processor (installed in "Setup tools" step)
- **gh CLI**: GitHub CLI (pre-installed in GitHub Actions)
- **GITHUB_TOKEN**: Automatically available in GitHub Actions

### Permissions

For persisting variables across runs, the workflow needs:

```yaml
permissions:
  contents: read
  actions: write
```

Without these permissions, the script will still set variables for the current run but won't persist them.

## Local Execution

You can run the script locally (though it's designed for CI):

```bash
# Install requirements
brew install jq gh  # macOS
# or
sudo apt-get install jq gh  # Linux

# Authenticate gh CLI
gh auth login

# Run script
export ENV_NAME=copilot
scripts/resolve_beefy_vaults.sh
```

## Advantages

### Automatic Updates
- Vault addresses may change when Beefy updates strategies
- The script always fetches the latest addresses
- No manual updates needed

### Immediate Execution
- Variables are set in `$GITHUB_ENV` for immediate use
- Strategy runs with all 21 pools once the required addresses are resolved automatically

### Persistence
- Variables are saved to GitHub Environment (if permissions allow)
- Future runs use cached values
- Falls back to API query if cache is stale

## Fallback Behavior

If the script cannot find a vault:
- Logs a warning message
- Does not set the environment variable
- Strategy gracefully skips pools without addresses
- Other pools continue to work normally

## Troubleshooting

### Script Not Finding Vaults

Check the filters in the script. Beefy may have changed:
- Platform name (look for "aerodrome", "aero", "cow")
- Asset naming convention
- Vault ID format

### Permission Denied for Variable Setting

The `gh variable set` command requires:
- Valid `GH_TOKEN` with appropriate scope
- Environment must exist and be accessible
- User/token must have write access to environment

### jq Not Found

Ensure the "Setup tools" step runs before the resolution step:

```yaml
- name: Setup tools
  run: sudo apt-get update && sudo apt-get install -y jq
```

## Manual Override

You can still manually set vault addresses if needed:

1. Go to repository Settings → Environments → copilot
2. Add variables with the vault addresses
3. The workflow will use manual values if set, otherwise resolves automatically

## Monitoring

Check the workflow logs for the "Resolve Beefy vaults" step:

```
Scarico vaults Beefy...
✓ BEEFY_USDC_USDT_VAULT = 0x...
✓ BEEFY_WETH_USDC_VAULT = 0x...
✓ BEEFY_WETH_USDT_VAULT = 0x...
✓ BEEFY_CBETH_WETH_VAULT = 0x...
Beefy vaults (runtime):
BEEFY_USDC_USDT_VAULT=0x...
...
```

## Future Enhancements

Potential improvements:
- Add more platforms (Uniswap V3, Curve, etc.)
- Support more chains
- Cache API responses to reduce calls
- Validate vault addresses on-chain before using
- Add health checks for vault performance
