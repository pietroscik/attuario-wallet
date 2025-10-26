#!/usr/bin/env python3
"""Verifica rapido della configurazione Aave v3 su Base."""

import os
from pathlib import Path

from web3 import HTTPProvider, Web3

# Leggi variabili env (puoi anche passare via CLI)
RPC_URL = os.environ.get("RPC_URL", "https://mainnet.base.org")
POOL_ADDR = (
    os.environ.get("AAVE_POOL_ADDRESS")
    or os.environ.get("AAVE_POOL_ADDRESS_8453")
    or "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5"
)

# ABI minimal per IPool getReservesList
IPool_ABI = [
    {
        "inputs": [],
        "name": "getReservesList",
        "outputs": [
            {"internalType": "address[]", "name": "", "type": "address[]"}
        ],
        "stateMutability": "view",
        "type": "function",
    }
]

w3 = Web3(HTTPProvider(RPC_URL, request_kwargs={"timeout": 20}))
assert w3.is_connected(), f"Web3 non connesso ({RPC_URL})"
print(f"Connesso a RPC: {RPC_URL}")
print(f"chainId: {w3.eth.chain_id}")

pool = w3.eth.contract(address=Web3.to_checksum_address(POOL_ADDR), abi=IPool_ABI)
assets = pool.functions.getReservesList().call()
print(f"Pool address: {POOL_ADDR}")
print(f"Numero asset supportati: {len(assets)}")

# Mostra i primi indirizzi per conferma
max_show = 10
for addr in assets[:max_show]:
    print(" -", addr)
if len(assets) > max_show:
    print(" ...")

print("Test completato con successo")
