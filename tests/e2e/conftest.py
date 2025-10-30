import os, pytest
from web3 import Web3

def pytest_addoption(parser):
    parser.addoption("--rpc", action="store", default=os.getenv("FORK_RPC_URL"))

@pytest.fixture(scope="session")
def rpc_url(pytestconfig):
    return pytestconfig.getoption("--rpc")

@pytest.fixture(scope="session")
def w3(rpc_url):
    if not rpc_url:
        pytest.skip("FORK_RPC_URL non impostata")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    assert w3.is_connected(), "Connessione RPC fallita"
    return w3
