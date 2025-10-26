#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Abstract adapter interface for portfolio operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict


class Adapter(ABC):
    @abstractmethod
    def deposit_all(self) -> Dict[str, object]:
        """Deposit the available asset balance into the target protocol."""

    @abstractmethod
    def withdraw_all(self) -> Dict[str, object]:
        """Withdraw the maximum redeemable amount from the target protocol."""
