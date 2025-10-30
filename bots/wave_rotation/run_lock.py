#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Run-lock mechanism to prevent concurrent strategy executions."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
LOCK_FILE = BASE_DIR / ".run_lock"


class RunLockError(Exception):
    """Raised when unable to acquire run lock."""
    pass


class RunLock:
    """Context manager for ensuring idempotent execution (no concurrent runs)."""

    def __init__(self, timeout_seconds: int = 3600):
        """
        Initialize run lock.
        
        Args:
            timeout_seconds: Maximum age of stale lock file before considering it abandoned
        """
        self.lock_file = LOCK_FILE
        self.timeout_seconds = timeout_seconds
        self.acquired = False

    def __enter__(self) -> "RunLock":
        """Acquire the lock or raise RunLockError."""
        if self.lock_file.exists():
            # Check if lock is stale
            try:
                lock_age = time.time() - self.lock_file.stat().st_mtime
                if lock_age < self.timeout_seconds:
                    raise RunLockError(
                        f"Another strategy execution is in progress (lock age: {int(lock_age)}s)"
                    )
                # Stale lock - remove it
                self.lock_file.unlink()
            except (OSError, PermissionError) as exc:
                raise RunLockError(f"Cannot access lock file: {exc}") from exc

        # Create lock file
        try:
            self.lock_file.write_text(f"{os.getpid()}\n{time.time()}\n")
            self.acquired = True
        except (OSError, PermissionError) as exc:
            raise RunLockError(f"Cannot create lock file: {exc}") from exc

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release the lock."""
        if self.acquired and self.lock_file.exists():
            try:
                self.lock_file.unlink()
            except (OSError, PermissionError):
                # Best effort cleanup
                pass
        return False


def acquire_run_lock(timeout_seconds: int = 3600) -> RunLock:
    """
    Acquire a run lock to prevent concurrent executions.
    
    Args:
        timeout_seconds: Maximum age of stale lock before removal
        
    Returns:
        RunLock context manager
        
    Raises:
        RunLockError: If lock cannot be acquired
    """
    return RunLock(timeout_seconds=timeout_seconds)
