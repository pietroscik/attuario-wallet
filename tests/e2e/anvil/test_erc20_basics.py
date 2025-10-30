import os, pytest
from web3 import Web3
pytestmark = pytest.mark.fork

ERC20 = [
    {"name":"decimals","type":"function","stateMutability":"view","inputs":[],"outputs":[{"type":"uint8"}]},
    {"name":"symbol","type":"function","stateMutability":"view","inputs":[],"outputs":[{"type":"string"}]},
]

def test_usdc_or_weth_metadata(w3):
    addr = os.getenv("USDC_BASE") or os.getenv("WETH_TOKEN_ADDRESS")
    if not addr:
        pytest.skip("USDC_BASE o WETH_TOKEN_ADDRESS non impostati")
    c = w3.eth.contract(Web3.to_checksum_address(addr), abi=ERC20)
    assert c.functions.decimals().call() > 0
    assert len(c.functions.symbol().call()) > 0
