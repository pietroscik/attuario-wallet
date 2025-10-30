import os, pytest
from web3 import Web3
def pytest_addoption(parser):
    parser.addoption("--rpc", action="store", default=os.getenv("FORK_RPC_URL"))
@pytest.fixture(scope="session")
def w3(pytestconfig):
    rpc = pytestconfig.getoption("--rpc")
    if not rpc:
        pytest.skip("FORK_RPC_URL non impostata")
    w3 = Web3(Web3.HTTPProvider(rpc))
    assert w3.is_connected(), "Connessione RPC fallita"
    return w3
