import pytest

from expanse.encryption.key import Key
from expanse.encryption.key_chain import KeyChain


@pytest.fixture
def key1() -> Key:
    return Key(b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb")


@pytest.fixture
def key2() -> Key:
    return Key(b"73NBdlFeA2L1rP-GDasaIFOKYZMIWo07")


def test_key_chain_can_be_created_with_keys(key1: Key, key2: Key) -> None:
    key_chain = KeyChain([key1, key2])

    assert len(key_chain) == 2
    assert key_chain.latest.value == key1.value


def test_key_chain_can_add_keys(key1: Key, key2: Key) -> None:
    key_chain = KeyChain([key1])

    key_chain.add(key2)

    assert len(key_chain) == 2
    assert key_chain.latest.value == key1.value


def test_key_chain_can_iterate_over_keys(key1: Key, key2: Key) -> None:
    key_chain = KeyChain([key1, key2])

    keys = list(key_chain)

    assert len(keys) == 2
    assert keys[0].value == key1.value
    assert keys[1].value == key2.value
