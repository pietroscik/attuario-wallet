#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Auto adapter registry with probe caching."""

from __future__ import annotations

import os
from typing import Tuple

try:  # Optional dependency – Web3 is needed only for on-chain probing
    from web3 import Web3
except ModuleNotFoundError:  # pragma: no cover - import guard branch
    Web3 = None  # type: ignore[assignment]

if Web3 is not None:
    from adapters_auto.aavev3_auto import AaveV3Auto
    from adapters_auto.beefy_auto import BeefyAuto
    from adapters_auto.comet_auto import CometAuto
    from adapters_auto.ctoken_auto import CTokenAuto
    from adapters_auto.erc4626_auto import ERC4626Auto
    from adapters_auto.yearn_auto import YearnAuto

    AUTO_CLASSES = [
        ("ERC4626", ERC4626Auto),
        ("BEEFY", BeefyAuto),
        ("YEARN", YearnAuto),
        ("COMET", CometAuto),
        ("CTOKEN", CTokenAuto),
        ("AAVEV3", AaveV3Auto),
    ]
else:  # pragma: no cover - used only in environments without web3
    AUTO_CLASSES = []


def probe_type(w3: Web3, address: str) -> Tuple[bool, str, object | None]:
    if Web3 is None:
        return False, "none", None

    for name, cls in AUTO_CLASSES:
        try:
            if name == "AAVEV3":
                chain_id = w3.eth.chain_id
                if not (os.getenv(f"AAVE_POOL_ADDRESS_{chain_id}") or os.getenv("AAVE_POOL_ADDRESS")):
                    continue
            if cls.probe(w3, address):
                return True, name, cls
        except Exception:
            continue
    return False, "none", None


def pick_auto_adapter(w3: Web3, address: str, signer, sender: str):
    if Web3 is None:
        return None, "web3_missing"

    ok, adapter_type, cls = probe_type(w3, address)
    if not ok:
        return None, "none"
    return cls(w3, signer, sender, address), adapter_type
