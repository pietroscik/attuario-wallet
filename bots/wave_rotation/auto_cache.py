#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Cache helpers for auto adapter detection."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

CACHE_PATH = Path("cache/auto_adapter_cache.json")


def _load_cache() -> Dict[str, Any]:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text())
        except Exception:
            return {"by_pool": {}, "ts": time.time()}
    return {"by_pool": {}, "ts": time.time()}


def _save_cache(cache: Dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2))


def get_cached(pool_id: str, ttl_hours: float = 168.0):
    cache = _load_cache()
    entry = cache["by_pool"].get(pool_id)
    if not entry:
        return None
    if (time.time() - entry.get("ts", 0)) > ttl_hours * 3600:
        return None
    return entry


def set_cached(pool_id: str, adapter_type: str | None, *, reason: str = "") -> None:
    cache = _load_cache()
    cache["by_pool"][pool_id] = {
        "type": adapter_type or "none",
        "reason": reason,
        "ts": time.time(),
    }
    _save_cache(cache)
