import os, pytest
from web3 import Web3
pytestmark = pytest.mark.fork
ERC20 = [
 {"name":"decimals","type":"function","stateMutability":"view","inputs":[],"outputs":[{"type":"uint8"}]},
 {"name":"symbol","type":"function","stateMutability":"view","inputs":[],"outputs":[{"type":"string"}]},
]
def test_weth_usdc_metadata(w3):
    weth = os.getenv("WETH_TOKEN_ADDRESS") or "0x4200000000000000000000000000000000000006"
    usdc = os.getenv("USDC_BASE") or "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    for addr in (weth, usdc):
        c = w3.eth.contract(Web3.to_checksum_address(addr), abi=ERC20)
        assert c.functions.decimals().call() > 0
        assert len(c.functions.symbol().call()) > 0
