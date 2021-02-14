import pytest

INITIAL_VALUE = 4


@pytest.fixture
def storage_contract(Storage, accounts):
    # deploy the contract with the initial value as a constructor argument
    yield Storage.deploy(INITIAL_VALUE, {'from': accounts[0]})


def test_initial_state(storage_contract):
    # Check if the constructor of the contract is set up properly
    assert storage_contract.storedData() == INITIAL_VALUE


def test_set(storage_contract, accounts):
    # set the value to 10
    storage_contract.set(10, {'from': accounts[0]})
    assert storage_contract.storedData() == 10  # Directly access storedData

    # set the value to -5
    storage_contract.set(-5, {'from': accounts[0]})
    assert storage_contract.storedData() == -5
