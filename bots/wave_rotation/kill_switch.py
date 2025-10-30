#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Kill-switch mechanism to halt execution on consecutive on-chain errors."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
KILL_SWITCH_FILE = BASE_DIR / ".kill_switch_state"


@dataclass
class KillSwitchState:
    """State tracking for kill-switch mechanism."""
    
    consecutive_errors: int = 0
    last_error_time: Optional[float] = None
    last_error_message: Optional[str] = None
    triggered: bool = False
    triggered_at: Optional[float] = None
    
    @classmethod
    def load(cls, path: Path = KILL_SWITCH_FILE) -> "KillSwitchState":
        """Load state from file."""
        if not path.exists():
            return cls()
        
        try:
            data = json.loads(path.read_text())
            return cls(
                consecutive_errors=int(data.get("consecutive_errors", 0)),
                last_error_time=data.get("last_error_time"),
                last_error_message=data.get("last_error_message"),
                triggered=bool(data.get("triggered", False)),
                triggered_at=data.get("triggered_at"),
            )
        except (json.JSONDecodeError, ValueError, KeyError):
            return cls()
    
    def save(self, path: Path = KILL_SWITCH_FILE) -> None:
        """Save state to file."""
        data = {
            "consecutive_errors": self.consecutive_errors,
            "last_error_time": self.last_error_time,
            "last_error_message": self.last_error_message,
            "triggered": self.triggered,
            "triggered_at": self.triggered_at,
        }
        path.write_text(json.dumps(data, indent=2))


class KillSwitch:
    """
    Kill-switch to halt execution after consecutive on-chain errors.
    
    Tracks consecutive errors and triggers halt when threshold is exceeded.
    Automatically resets after a successful operation or timeout period.
    """
    
    def __init__(
        self,
        threshold: int = 3,
        reset_timeout: float = 3600.0,
        state_file: Path = KILL_SWITCH_FILE,
    ):
        """
        Initialize kill-switch.
        
        Args:
            threshold: Number of consecutive errors before triggering
            reset_timeout: Seconds after which error count resets
            state_file: Path to state persistence file
        """
        self.threshold = max(1, threshold)
        self.reset_timeout = max(0.0, reset_timeout)
        self.state_file = state_file
        self.state = KillSwitchState.load(state_file)
    
    @classmethod
    def from_env(cls) -> "KillSwitch":
        """Create kill-switch from environment configuration."""
        threshold = int(os.getenv("KILL_SWITCH_THRESHOLD", "3"))
        reset_timeout = float(os.getenv("KILL_SWITCH_RESET_TIMEOUT", "3600"))
        return cls(threshold=threshold, reset_timeout=reset_timeout)
    
    def _should_reset_counter(self) -> bool:
        """Check if error counter should be reset due to timeout."""
        if self.state.last_error_time is None:
            return False
        
        elapsed = time.time() - self.state.last_error_time
        return elapsed > self.reset_timeout
    
    def check(self) -> None:
        """
        Check if kill-switch is triggered.
        
        Raises:
            RuntimeError: If kill-switch is triggered
        """
        if self.state.triggered:
            elapsed = time.time() - (self.state.triggered_at or 0.0)
            raise RuntimeError(
                f"Kill-switch triggered: {self.state.consecutive_errors} consecutive errors. "
                f"Last error: {self.state.last_error_message}. "
                f"Triggered {int(elapsed)}s ago. Manual reset required."
            )
    
    def record_error(self, error_message: str) -> None:
        """
        Record an on-chain error occurrence.
        
        Args:
            error_message: Description of the error
        """
        now = time.time()
        
        # Reset counter if timeout exceeded
        if self._should_reset_counter():
            self.state.consecutive_errors = 0
        
        # Increment error count
        self.state.consecutive_errors += 1
        self.state.last_error_time = now
        self.state.last_error_message = error_message
        
        # Check if threshold exceeded
        if self.state.consecutive_errors >= self.threshold and not self.state.triggered:
            self.state.triggered = True
            self.state.triggered_at = now
        
        self.state.save(self.state_file)
    
    def record_success(self) -> None:
        """Record a successful operation (resets error counter)."""
        self.state.consecutive_errors = 0
        self.state.last_error_time = None
        self.state.last_error_message = None
        self.state.save(self.state_file)
    
    def reset(self) -> None:
        """Manually reset kill-switch (including triggered state)."""
        self.state = KillSwitchState()
        self.state.save(self.state_file)
    
    def status(self) -> dict:
        """
        Get current kill-switch status.
        
        Returns:
            Dictionary with status information
        """
        return {
            "triggered": self.state.triggered,
            "consecutive_errors": self.state.consecutive_errors,
            "threshold": self.threshold,
            "last_error": self.state.last_error_message,
            "last_error_time": self.state.last_error_time,
            "triggered_at": self.state.triggered_at,
        }


# Global instance (lazy initialization)
_global_kill_switch: Optional[KillSwitch] = None


def get_kill_switch() -> KillSwitch:
    """Get global kill-switch instance."""
    global _global_kill_switch
    if _global_kill_switch is None:
        _global_kill_switch = KillSwitch.from_env()
    return _global_kill_switch
