#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Protocol state detection (paused, shutdown, emergency) utilities."""

from __future__ import annotations

from typing import Optional, Tuple

try:
    from web3 import Web3
    from web3.contract.contract import Contract
except ModuleNotFoundError:
    Web3 = None  # type: ignore[assignment]
    Contract = None  # type: ignore[assignment]


# Common ABI fragments for state checking
PAUSED_ABI = [
    {
        "name": "paused",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "bool"}],
    }
]

SHUTDOWN_ABI = [
    {
        "name": "shutdown",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "bool"}],
    }
]

EMERGENCY_ABI = [
    {
        "name": "emergencyShutdown",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "bool"}],
    }
]


def check_paused_state(
    contract: Optional[Contract] = None,
    address: Optional[str] = None,
    w3 = None,
) -> Tuple[bool, str]:
    """
    Check if protocol/vault is paused.
    
    Args:
        contract: Contract instance (if available)
        address: Contract address (if contract not provided)
        w3: Web3 instance (required if address provided)
        
    Returns:
        Tuple of (is_operational, status_message)
        - is_operational: True if protocol is operational, False if paused/shutdown
        - status_message: Description of state
    """
    if Web3 is None:
        return True, "check_disabled:web3_missing"
    
    # Try to get contract if not provided
    if contract is None and address and w3:
        try:
            address = Web3.to_checksum_address(address)
        except Exception:
            return True, "check_skipped:invalid_address"
    
    # Check paused() method
    if contract is not None or (address and w3):
        try:
            if contract is None:
                contract = w3.eth.contract(address=address, abi=PAUSED_ABI)
            
            if hasattr(contract.functions, 'paused'):
                is_paused = contract.functions.paused().call()
                if is_paused:
                    return False, "paused:true"
        except Exception as exc:
            # Method doesn't exist or call failed - continue checking other methods
            pass
    
    # Check shutdown() method
    if contract is not None or (address and w3):
        try:
            if contract is None:
                contract = w3.eth.contract(address=address, abi=SHUTDOWN_ABI)
            
            if hasattr(contract.functions, 'shutdown'):
                is_shutdown = contract.functions.shutdown().call()
                if is_shutdown:
                    return False, "shutdown:true"
        except Exception:
            pass
    
    # Check emergencyShutdown() method (Yearn-style)
    if contract is not None or (address and w3):
        try:
            if contract is None:
                contract = w3.eth.contract(address=address, abi=EMERGENCY_ABI)
            
            if hasattr(contract.functions, 'emergencyShutdown'):
                is_emergency = contract.functions.emergencyShutdown().call()
                if is_emergency:
                    return False, "emergency_shutdown:true"
        except Exception:
            pass
    
    return True, "operational"


def check_vault_state_erc4626(vault_contract) -> Tuple[bool, str]:
    """
    Check ERC-4626 vault operational state.
    
    Args:
        vault_contract: ERC-4626 vault contract
        
    Returns:
        Tuple of (is_operational, status_message)
    """
    try:
        # Check if deposits are enabled via maxDeposit
        # If maxDeposit returns 0, deposits are disabled
        if hasattr(vault_contract.functions, 'maxDeposit'):
            max_deposit = vault_contract.functions.maxDeposit(
                "0x0000000000000000000000000000000000000000"
            ).call()
            if max_deposit == 0:
                return False, "deposits_disabled:maxDeposit=0"
    except Exception:
        pass
    
    # Check paused state
    return check_paused_state(contract=vault_contract)


def check_yearn_vault_state(vault_contract) -> Tuple[bool, str]:
    """
    Check Yearn vault operational state.
    
    Args:
        vault_contract: Yearn vault contract
        
    Returns:
        Tuple of (is_operational, status_message)
    """
    try:
        # Check emergencyShutdown first (Yearn v2/v3)
        if hasattr(vault_contract.functions, 'emergencyShutdown'):
            is_shutdown = vault_contract.functions.emergencyShutdown().call()
            if is_shutdown:
                return False, "yearn_emergency_shutdown:true"
    except Exception:
        pass
    
    try:
        # Check depositLimit (if 0, deposits disabled)
        if hasattr(vault_contract.functions, 'depositLimit'):
            deposit_limit = vault_contract.functions.depositLimit().call()
            if deposit_limit == 0:
                return False, "deposits_disabled:depositLimit=0"
    except Exception:
        pass
    
    return check_paused_state(contract=vault_contract)


def check_aave_pool_state(pool_contract) -> Tuple[bool, str]:
    """
    Check Aave pool operational state.
    
    Args:
        pool_contract: Aave pool contract
        
    Returns:
        Tuple of (is_operational, status_message)
    """
    # Aave v3 has paused() method on pool
    return check_paused_state(contract=pool_contract)


def check_beefy_vault_state(vault_contract) -> Tuple[bool, str]:
    """
    Check Beefy vault operational state.
    
    Args:
        vault_contract: Beefy vault contract
        
    Returns:
        Tuple of (is_operational, status_message)
    """
    try:
        # Beefy vaults have paused() method
        if hasattr(vault_contract.functions, 'paused'):
            is_paused = vault_contract.functions.paused().call()
            if is_paused:
                return False, "beefy_paused:true"
    except Exception:
        pass
    
    return True, "operational"


def should_block_deposit(
    protocol_type: str,
    contract,
    address: Optional[str] = None,
    w3 = None,
) -> Tuple[bool, str]:
    """
    Determine if deposit should be blocked based on protocol state.
    
    Args:
        protocol_type: Type of protocol (erc4626, yearn, aave_v3, beefy, etc.)
        contract: Contract instance
        address: Contract address (fallback)
        w3: Web3 instance
        
    Returns:
        Tuple of (should_block, reason)
    """
    protocol_checkers = {
        "erc4626": check_vault_state_erc4626,
        "yearn": check_yearn_vault_state,
        "aave_v3": check_aave_pool_state,
        "beefy": check_beefy_vault_state,
        "beefy_vault": check_beefy_vault_state,
    }
    
    checker = protocol_checkers.get(protocol_type.lower())
    
    if checker and contract is not None:
        is_operational, status = checker(contract)
        return not is_operational, status
    
    # Fallback to generic check
    is_operational, status = check_paused_state(contract, address, w3)
    return not is_operational, status
