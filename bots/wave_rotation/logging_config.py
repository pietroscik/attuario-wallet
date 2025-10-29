#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Structured logging configuration for Attuario Wave Rotation.

This module provides a centralized logging configuration with proper
log levels, formatting, and handlers. It replaces the scattered print()
statements throughout the codebase with structured logging.

Usage:
    from logging_config import get_logger
    
    logger = get_logger(__name__)
    logger.info("Strategy execution started")
    logger.error("Failed to fetch data", extra={"url": url, "error": str(e)})
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Valid log levels
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

# Default log level from environment or INFO (validated)
_raw_level = os.getenv("LOG_LEVEL", "INFO").upper()
DEFAULT_LOG_LEVEL = _raw_level if _raw_level in VALID_LOG_LEVELS else "INFO"

# Default log format with timestamp, level, module, and message
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# ISO 8601 timestamp format
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# Global logger registry to avoid duplicate handlers
_loggers: dict[str, logging.Logger] = {}
_configured = False


def configure_logging(
    level: str = DEFAULT_LOG_LEVEL,
    log_file: Optional[Path] = None,
    console: bool = True,
    format_string: str = DEFAULT_LOG_FORMAT,
) -> None:
    """Configure root logger with handlers and formatting.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        console: Whether to log to console (default: True)
        format_string: Log message format string
    """
    global _configured
    
    if _configured:
        return
    
    # Get root logger
    root = logging.getLogger()
    
    # Set level
    try:
        log_level = getattr(logging, level)
    except AttributeError:
        log_level = logging.INFO
    
    root.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(format_string, datefmt=TIMESTAMP_FORMAT)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)
    
    # File handler
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except Exception as e:
            # Fallback to console only
            print(f"Warning: Failed to create log file {log_file}: {e}", file=sys.stderr)
    
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with the given name.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
        
    Returns:
        Configured logger instance
        
    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting process")
        >>> logger.error("Failed to connect", extra={"host": "example.com"})
    """
    if not _configured:
        # Auto-configure on first use
        log_path_str = os.getenv("LOG_PATH")
        log_path = Path(log_path_str) if log_path_str else None
        configure_logging(log_file=log_path)
    
    if name in _loggers:
        return _loggers[name]
    
    logger = logging.getLogger(name)
    _loggers[name] = logger
    return logger


def set_log_level(level: str) -> None:
    """Change the log level for all configured loggers.
    
    Args:
        level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    try:
        log_level = getattr(logging, level.upper())
        logging.getLogger().setLevel(log_level)
        for handler in logging.getLogger().handlers:
            handler.setLevel(log_level)
    except AttributeError:
        print(f"Warning: Invalid log level '{level}'", file=sys.stderr)


# Convenience functions for backward compatibility
def log_info(message: str, **kwargs) -> None:
    """Log an info message (backward compatibility)."""
    get_logger("attuario").info(message, extra=kwargs)


def log_warning(message: str, **kwargs) -> None:
    """Log a warning message (backward compatibility)."""
    get_logger("attuario").warning(message, extra=kwargs)


def log_error(message: str, **kwargs) -> None:
    """Log an error message (backward compatibility)."""
    get_logger("attuario").error(message, extra=kwargs)


def log_debug(message: str, **kwargs) -> None:
    """Log a debug message (backward compatibility)."""
    get_logger("attuario").debug(message, extra=kwargs)


if __name__ == "__main__":
    # Example usage
    configure_logging(level="DEBUG")
    
    logger = get_logger(__name__)
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # With extra context
    logger.info("API call successful", extra={"endpoint": "/pools", "duration_ms": 123})
