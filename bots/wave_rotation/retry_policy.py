#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Retry policy with exponential backoff for transaction operations."""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Optional, TypeVar

from tx_errors import (
    NonceError,
    GasError,
    TimeoutError,
    TransactionError,
    classify_error,
)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before first retry
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
        """
        self.max_attempts = max(1, max_attempts)
        self.initial_delay = max(0.0, initial_delay)
        self.max_delay = max(self.initial_delay, max_delay)
        self.exponential_base = max(1.0, exponential_base)
        self.jitter = jitter
    
    @classmethod
    def from_env(cls) -> "RetryConfig":
        """Load retry configuration from environment variables."""
        return cls(
            max_attempts=int(os.getenv("TX_RETRY_MAX_ATTEMPTS", "3")),
            initial_delay=float(os.getenv("TX_RETRY_INITIAL_DELAY", "1.0")),
            max_delay=float(os.getenv("TX_RETRY_MAX_DELAY", "30.0")),
            exponential_base=float(os.getenv("TX_RETRY_EXPONENTIAL_BASE", "2.0")),
            jitter=os.getenv("TX_RETRY_JITTER", "true").lower() in ("true", "1", "yes"),
        )
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.
        
        Args:
            attempt: Attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        delay = self.initial_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter and delay > 0:
            # Add ±25% jitter
            import random
            jitter_amount = delay * 0.25
            delay = delay + random.uniform(-jitter_amount, jitter_amount)
            delay = max(0.0, delay)
        
        return delay


def should_retry(error: Exception, attempt: int, config: RetryConfig) -> bool:
    """
    Determine if operation should be retried based on error type.
    
    Args:
        error: Exception that occurred
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
        
    Returns:
        True if should retry, False otherwise
    """
    # Exceeded max attempts
    if attempt >= config.max_attempts - 1:
        return False
    
    # Classify as transaction error if not already
    if not isinstance(error, TransactionError):
        error_str = str(error)
        error = classify_error(error_str)
    
    # Don't retry certain error types
    if isinstance(error, (NonceError, GasError)):
        # These usually require manual intervention
        return False
    
    # Retry timeouts and generic transaction errors
    if isinstance(error, (TimeoutError, TransactionError)):
        return True
    
    return False


def retry_with_backoff(
    func: Callable[..., T],
    *args: Any,
    config: Optional[RetryConfig] = None,
    **kwargs: Any,
) -> T:
    """
    Execute function with retry and exponential backoff.
    
    Args:
        func: Function to execute
        *args: Positional arguments for function
        config: Retry configuration (defaults to env-based config)
        **kwargs: Keyword arguments for function
        
    Returns:
        Function return value
        
    Raises:
        Last exception if all retries exhausted
    """
    if config is None:
        config = RetryConfig.from_env()
    
    last_error: Optional[Exception] = None
    
    for attempt in range(config.max_attempts):
        try:
            return func(*args, **kwargs)
        except Exception as error:
            last_error = error
            
            if not should_retry(error, attempt, config):
                raise
            
            # Calculate and apply delay before retry
            if attempt < config.max_attempts - 1:
                delay = config.get_delay(attempt)
                if delay > 0:
                    time.sleep(delay)
    
    # Should not reach here, but raise last error if we do
    if last_error:
        raise last_error
    
    raise RuntimeError("Retry logic error: no attempts executed")
