#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""ERC-4626 adapter implementing deposit/withdraw all operations."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Optional

from web3 import Web3

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from abi_min import ERC20_ABI, ERC4626_ABI
from .base import Adapter

try:
    from protocol_state import check_vault_state_erc4626
    from safe_math import safe_decimals, clamp_to_balance
    from slippage import create_slippage_config
except ImportError:
    # Fallback for when imports are not available
    check_vault_state_erc4626 = None
    safe_decimals = None
    clamp_to_balance = None
    create_slippage_config = None


MAX_UINT256 = (1 << 256) - 1


class ERC4626Adapter(Adapter):
    def __init__(self, w3: Web3, config: Dict[str, object], signer, sender: str):
        self.w3 = w3
        self.signer = signer
        self.sender = Web3.to_checksum_address(sender)
        self.vault = w3.eth.contract(
            address=Web3.to_checksum_address(str(config["vault"])), abi=ERC4626_ABI
        )
        self.asset = w3.eth.contract(
            address=Web3.to_checksum_address(str(config["asset"])), abi=ERC20_ABI
        )

    # Common helpers -----------------------------------------------------
    def _get_nonce(self) -> int:
        return self.w3.eth.get_transaction_count(self.sender)

    def _simulate(self, tx: Dict[str, object]) -> None:
        call_tx = {k: tx[k] for k in ("to", "from", "data") if k in tx}
        call_tx["value"] = tx.get("value", 0)
        self.w3.eth.call(call_tx)

    def _sign_and_send(self, tx: Dict[str, object], nonce: Optional[int] = None) -> str:
        tx.setdefault("chainId", self.w3.eth.chain_id)
        tx.setdefault("from", self.sender)
        if nonce is None:
            nonce = self._get_nonce()
        tx["nonce"] = nonce

        if "gas" not in tx:
            tx["gas"] = self.w3.eth.estimate_gas(tx)

        gas_price = self.w3.eth.gas_price
        if "maxFeePerGas" not in tx:
            tx["maxFeePerGas"] = gas_price
        if "maxPriorityFeePerGas" not in tx:
            tx["maxPriorityFeePerGas"] = gas_price

        self._simulate(tx)

        signed = self.signer.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    # Token allowances / balances ---------------------------------------
    def _allowance(self) -> int:
        return self.asset.functions.allowance(self.sender, self.vault.address).call()

    def _approve_if_needed(self, amount: int, nonce: int, mode: Optional[str] = None) -> Optional[str]:
        allowance = self._allowance()
        if allowance >= amount:
            return None

        if mode is None:
            mode = os.getenv("ALLOWANCE_MODE", "MAX").strip().upper()
        approve_amount = MAX_UINT256 if mode == "MAX" else amount

        tx = self.asset.functions.approve(self.vault.address, approve_amount).build_transaction(
            {"from": self.sender}
        )
        return self._sign_and_send(tx, nonce=nonce)

    def _asset_balance(self) -> int:
        return self.asset.functions.balanceOf(self.sender).call()

    def _max_redeem(self) -> int:
        return self.vault.functions.maxRedeem(self.sender).call()

    # Adapter API --------------------------------------------------------
    def deposit_all(self) -> Dict[str, object]:
        # Check if vault is operational (paused/shutdown detection)
        if check_vault_state_erc4626 is not None:
            is_operational, status_msg = check_vault_state_erc4626(self.vault)
            if not is_operational:
                return {"status": "blocked", "reason": status_msg}
        
        amount = self._asset_balance()
        if amount <= 0:
            return {"status": "no_assets"}
        
        # Validate decimals and clamp amount safely
        if safe_decimals is not None:
            try:
                asset_decimals = self.asset.functions.decimals().call()
                asset_decimals = safe_decimals(asset_decimals, default=18)
            except Exception:
                asset_decimals = 18
        
        # Check preview for expected shares (slippage protection)
        try:
            expected_shares = self.vault.functions.previewDeposit(amount).call()
            if expected_shares <= 0:
                return {"status": "preview_failed", "reason": "Expected shares is 0"}
        except Exception as exc:
            # Preview failed - proceed cautiously
            expected_shares = None

        operations: Dict[str, object] = {
            "status": "ok",
            "assets": int(amount),
            "expected_shares": int(expected_shares) if expected_shares else None,
        }

        nonce = self._get_nonce()
        
        # Allowance policy: use exact approval mode for non-blue-chip or if configured
        allowance_mode = os.getenv("ALLOWANCE_MODE", "MAX").strip().upper()
        if os.getenv("VAULT_TRUSTED", "false").strip().lower() not in ("true", "1", "yes"):
            # Non-trusted vault: use exact approvals
            allowance_mode = "EXACT"
        
        approve_hash = self._approve_if_needed(amount, nonce, mode=allowance_mode)
        if approve_hash:
            operations["approve_tx"] = approve_hash
            nonce += 1

        deposit_tx = self.vault.functions.deposit(amount, self.sender).build_transaction(
            {"from": self.sender}
        )
        deposit_hash = self._sign_and_send(deposit_tx, nonce=nonce)
        operations["deposit_tx"] = deposit_hash
        return operations

    def withdraw_all(self) -> Dict[str, object]:
        shares = self._max_redeem()
        if shares <= 0:
            return {"status": "no_shares"}
        
        # Check preview for expected assets (sanity check)
        try:
            expected_assets = self.vault.functions.previewRedeem(shares).call()
        except Exception:
            expected_assets = None

        withdraw_tx = self.vault.functions.redeem(
            shares, self.sender, self.sender
        ).build_transaction({"from": self.sender})
        nonce = self._get_nonce()
        withdraw_hash = self._sign_and_send(withdraw_tx, nonce=nonce)
        
        result = {
            "status": "ok",
            "withdraw_tx": withdraw_hash,
            "shares": int(shares),
            "expected_assets": int(expected_assets) if expected_assets else None,
        }
        
        # Revoke allowance for non-trusted vaults after withdrawal
        if os.getenv("VAULT_TRUSTED", "false").strip().lower() not in ("true", "1", "yes"):
            if os.getenv("REVOKE_ALLOWANCE_ON_EXIT", "true").strip().lower() in ("true", "1", "yes"):
                try:
                    nonce += 1
                    revoke_hash = self._revoke_allowance(nonce)
                    if revoke_hash:
                        result["revoke_tx"] = revoke_hash
                except Exception:
                    # Best effort - don't fail withdrawal if revoke fails
                    pass
        
        return result
    
    def _revoke_allowance(self, nonce: int) -> Optional[str]:
        """Revoke token allowance (set to 0)."""
        tx = self.asset.functions.approve(self.vault.address, 0).build_transaction(
            {"from": self.sender}
        )
        return self._sign_and_send(tx, nonce=nonce)
