#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Execution summary reporting for strategy runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class ExecutionSummary:
    """Summary of strategy execution for reporting and observability."""
    
    run_id: str
    timestamp: str
    
    # Flags
    dry_run: bool = False
    multi_strategy: bool = False
    
    # Pool selection
    active_pool: Optional[str] = None
    adapter_type: Optional[str] = None
    pool_chain: Optional[str] = None
    
    # Amounts
    amount_in: Optional[float] = None
    amount_out: Optional[float] = None
    amount_unit: str = "ETH"
    
    # Gas & costs
    gas_used: Optional[int] = None
    gas_cost: Optional[float] = None
    gas_cost_unit: str = "ETH"
    
    # Performance
    realized_pnl: Optional[float] = None
    pnl_unit: str = "ETH"
    
    # Treasury
    treasury_move: bool = False
    treasury_amount: Optional[float] = None
    treasury_reason: Optional[str] = None
    
    # Execution status
    errors: int = 0
    warnings: int = 0
    error_messages: List[str] = field(default_factory=list)
    warning_messages: List[str] = field(default_factory=list)
    
    # Additional context
    notes: List[str] = field(default_factory=list)
    
    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors += 1
        self.error_messages.append(message)
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings += 1
        self.warning_messages.append(message)
    
    def add_note(self, note: str) -> None:
        """Add a note."""
        self.notes.append(note)
    
    def format_text(self) -> str:
        """
        Format execution summary as human-readable text.
        
        Returns:
            Formatted summary string
        """
        lines = [
            "=" * 60,
            "EXECUTION SUMMARY",
            "=" * 60,
            f"run_id={self.run_id}",
            f"timestamp={self.timestamp}",
            "",
            "FLAGS:",
            f"  DRY_RUN: {self.dry_run}",
            f"  MULTI_STRATEGY: {self.multi_strategy}",
            "",
        ]
        
        if self.active_pool:
            lines.extend([
                "POOL:",
                f"  active_pool: {self.active_pool}",
                f"  adapter: {self.adapter_type or 'unknown'}",
                f"  chain: {self.pool_chain or 'unknown'}",
                "",
            ])
        
        if self.amount_in is not None or self.amount_out is not None:
            lines.append("AMOUNTS:")
            if self.amount_in is not None:
                lines.append(f"  amount_in: {self.amount_in:.6f} {self.amount_unit}")
            if self.amount_out is not None:
                lines.append(f"  amount_out: {self.amount_out:.6f} {self.amount_unit}")
            lines.append("")
        
        if self.gas_used is not None or self.gas_cost is not None:
            lines.append("GAS:")
            if self.gas_used is not None:
                lines.append(f"  gas_used: {self.gas_used:,}")
            if self.gas_cost is not None:
                lines.append(f"  gas_cost: {self.gas_cost:.6f} {self.gas_cost_unit}")
            lines.append("")
        
        if self.realized_pnl is not None:
            sign = "+" if self.realized_pnl >= 0 else ""
            lines.extend([
                "PERFORMANCE:",
                f"  realized_pnl: {sign}{self.realized_pnl:.6f} {self.pnl_unit}",
                "",
            ])
        
        lines.extend([
            "TREASURY:",
            f"  treasury_move: {'YES' if self.treasury_move else 'NO'}",
        ])
        if self.treasury_amount is not None:
            lines.append(f"  treasury_amount: {self.treasury_amount:.6f} {self.amount_unit}")
        if self.treasury_reason:
            lines.append(f"  reason: {self.treasury_reason}")
        lines.append("")
        
        lines.extend([
            "STATUS:",
            f"  errors: {self.errors}",
            f"  warnings: {self.warnings}",
        ])
        
        if self.error_messages:
            lines.append("  error_details:")
            for msg in self.error_messages:
                lines.append(f"    - {msg}")
        
        if self.warning_messages:
            lines.append("  warning_details:")
            for msg in self.warning_messages:
                lines.append(f"    - {msg}")
        
        if self.notes:
            lines.append("")
            lines.append("NOTES:")
            for note in self.notes:
                lines.append(f"  - {note}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "flags": {
                "dry_run": self.dry_run,
                "multi_strategy": self.multi_strategy,
            },
            "pool": {
                "active_pool": self.active_pool,
                "adapter_type": self.adapter_type,
                "chain": self.pool_chain,
            } if self.active_pool else None,
            "amounts": {
                "amount_in": self.amount_in,
                "amount_out": self.amount_out,
                "unit": self.amount_unit,
            } if self.amount_in is not None or self.amount_out is not None else None,
            "gas": {
                "gas_used": self.gas_used,
                "gas_cost": self.gas_cost,
                "unit": self.gas_cost_unit,
            } if self.gas_used is not None or self.gas_cost is not None else None,
            "performance": {
                "realized_pnl": self.realized_pnl,
                "unit": self.pnl_unit,
            } if self.realized_pnl is not None else None,
            "treasury": {
                "treasury_move": self.treasury_move,
                "treasury_amount": self.treasury_amount,
                "reason": self.treasury_reason,
            },
            "status": {
                "errors": self.errors,
                "warnings": self.warnings,
                "error_messages": self.error_messages,
                "warning_messages": self.warning_messages,
            },
            "notes": self.notes,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


def create_execution_summary(
    dry_run: bool = False,
    multi_strategy: bool = False,
) -> ExecutionSummary:
    """
    Create a new execution summary.
    
    Args:
        dry_run: Whether this is a dry run
        multi_strategy: Whether multi-strategy is enabled
        
    Returns:
        ExecutionSummary instance
    """
    now = datetime.utcnow()
    run_id = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    return ExecutionSummary(
        run_id=run_id,
        timestamp=timestamp,
        dry_run=dry_run,
        multi_strategy=multi_strategy,
    )
