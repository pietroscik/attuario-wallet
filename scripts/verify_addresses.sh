#!/bin/bash
# ============================================================================
# Address Verification Script for Attuario Wallet
# ============================================================================
#
# This script helps verify ERC-20 tokens, LP tokens, and vault addresses
# on-chain using Foundry's cast tool.
#
# Prerequisites:
#   - Foundry installed (cast command available)
#   - RPC endpoint configured in environment variables
#
# Usage:
#   ./scripts/verify_addresses.sh <ADDRESS> <TYPE> [RPC_URL]
#
# Examples:
#   ./scripts/verify_addresses.sh 0x4200000000000000000000000000000000000006 token $BASE_RPC
#   ./scripts/verify_addresses.sh 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5 vault $BASE_RPC
#   ./scripts/verify_addresses.sh 0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43 router $BASE_RPC
#
# ============================================================================

set -e

# Check if cast is installed
if ! command -v cast &> /dev/null; then
    echo "❌ Error: 'cast' command not found. Please install Foundry:"
    echo "   curl -L https://foundry.paradigm.xyz | bash"
    echo "   foundryup"
    exit 1
fi

# Check arguments
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <ADDRESS> <TYPE> [RPC_URL]"
    echo ""
    echo "Types: token, lp, vault, router, pool"
    echo "Example: $0 0x4200000000000000000000000000000000000006 token https://mainnet.base.org"
    exit 1
fi

ADDRESS=$1
TYPE=$2
RPC_URL=${3:-${BASE_RPC:-"https://mainnet.base.org"}}

echo "============================================================================"
echo "Verifying Address: $ADDRESS"
echo "Type: $TYPE"
echo "RPC: $RPC_URL"
echo "============================================================================"
echo ""

# Function to call contract and handle errors
call_contract() {
    local address=$1
    local signature=$2
    local rpc=$3
    
    result=$(cast call "$address" "$signature" --rpc-url "$rpc" 2>&1 || echo "ERROR")
    echo "$result"
}

# Verify based on type
case $TYPE in
    token)
        echo "🔍 Verifying ERC-20 Token..."
        echo ""
        
        echo "Symbol:"
        symbol=$(call_contract "$ADDRESS" "symbol()(string)" "$RPC_URL")
        echo "  $symbol"
        
        echo ""
        echo "Name:"
        name=$(call_contract "$ADDRESS" "name()(string)" "$RPC_URL")
        echo "  $name"
        
        echo ""
        echo "Decimals:"
        decimals=$(call_contract "$ADDRESS" "decimals()(uint8)" "$RPC_URL")
        echo "  $decimals"
        
        echo ""
        echo "Total Supply:"
        totalSupply=$(call_contract "$ADDRESS" "totalSupply()(uint256)" "$RPC_URL")
        echo "  $totalSupply"
        
        if [[ "$symbol" == "ERROR"* ]] || [[ "$name" == "ERROR"* ]]; then
            echo ""
            echo "❌ Failed to verify as ERC-20 token"
            exit 1
        else
            echo ""
            echo "✅ Successfully verified as ERC-20 token: $symbol"
        fi
        ;;
        
    lp)
        echo "🔍 Verifying LP Token..."
        echo ""
        
        echo "Symbol:"
        symbol=$(call_contract "$ADDRESS" "symbol()(string)" "$RPC_URL")
        echo "  $symbol"
        
        echo ""
        echo "Token0:"
        token0=$(call_contract "$ADDRESS" "token0()(address)" "$RPC_URL")
        echo "  $token0"
        
        echo ""
        echo "Token1:"
        token1=$(call_contract "$ADDRESS" "token1()(address)" "$RPC_URL")
        echo "  $token1"
        
        echo ""
        echo "Reserves:"
        reserves=$(call_contract "$ADDRESS" "getReserves()(uint112,uint112,uint32)" "$RPC_URL")
        echo "  $reserves"
        
        if [[ "$token0" == "ERROR"* ]] || [[ "$token1" == "ERROR"* ]]; then
            echo ""
            echo "❌ Failed to verify as LP token"
            exit 1
        else
            echo ""
            echo "✅ Successfully verified as LP token: $symbol"
            echo "   Token0: $token0"
            echo "   Token1: $token1"
        fi
        ;;
        
    vault)
        echo "🔍 Verifying Vault..."
        echo ""
        
        # Try ERC-4626 vault interface
        echo "Asset (ERC-4626):"
        asset=$(call_contract "$ADDRESS" "asset()(address)" "$RPC_URL")
        echo "  $asset"
        
        # Try Beefy vault interface
        if [[ "$asset" == "ERROR"* ]]; then
            echo ""
            echo "Trying Beefy vault interface..."
            echo "Want:"
            want=$(call_contract "$ADDRESS" "want()(address)" "$RPC_URL")
            echo "  $want"
            
            echo ""
            echo "Balance:"
            balance=$(call_contract "$ADDRESS" "balance()(uint256)" "$RPC_URL")
            echo "  $balance"
            
            if [[ "$want" == "ERROR"* ]]; then
                echo ""
                echo "❌ Failed to verify as vault (tried ERC-4626 and Beefy)"
                exit 1
            else
                echo ""
                echo "✅ Successfully verified as Beefy vault"
                echo "   Want token: $want"
            fi
        else
            echo ""
            echo "Total Assets:"
            totalAssets=$(call_contract "$ADDRESS" "totalAssets()(uint256)" "$RPC_URL")
            echo "  $totalAssets"
            
            echo ""
            echo "✅ Successfully verified as ERC-4626 vault"
            echo "   Asset: $asset"
        fi
        ;;
        
    router)
        echo "🔍 Verifying Router..."
        echo ""
        
        echo "Factory:"
        factory=$(call_contract "$ADDRESS" "factory()(address)" "$RPC_URL")
        echo "  $factory"
        
        echo ""
        echo "WETH:"
        weth=$(call_contract "$ADDRESS" "WETH()(address)" "$RPC_URL")
        if [[ "$weth" == "ERROR"* ]]; then
            weth=$(call_contract "$ADDRESS" "weth()(address)" "$RPC_URL")
        fi
        echo "  $weth"
        
        if [[ "$factory" == "ERROR"* ]]; then
            echo ""
            echo "❌ Failed to verify as router"
            exit 1
        else
            echo ""
            echo "✅ Successfully verified as router"
            echo "   Factory: $factory"
            echo "   WETH: $weth"
        fi
        ;;
        
    pool)
        echo "🔍 Verifying Pool..."
        echo ""
        
        # Try Uniswap V3 pool
        echo "Token0:"
        token0=$(call_contract "$ADDRESS" "token0()(address)" "$RPC_URL")
        echo "  $token0"
        
        echo ""
        echo "Token1:"
        token1=$(call_contract "$ADDRESS" "token1()(address)" "$RPC_URL")
        echo "  $token1"
        
        echo ""
        echo "Fee:"
        fee=$(call_contract "$ADDRESS" "fee()(uint24)" "$RPC_URL")
        echo "  $fee"
        
        if [[ "$token0" == "ERROR"* ]] || [[ "$token1" == "ERROR"* ]]; then
            echo ""
            echo "❌ Failed to verify as pool"
            exit 1
        else
            echo ""
            echo "✅ Successfully verified as pool"
            echo "   Token0: $token0"
            echo "   Token1: $token1"
            echo "   Fee: $fee"
        fi
        ;;
        
    *)
        echo "❌ Unknown type: $TYPE"
        echo "Supported types: token, lp, vault, router, pool"
        exit 1
        ;;
esac

echo ""
echo "============================================================================"
