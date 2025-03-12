import pytest

from pytest_mock import MockerFixture

from expanse.encryption.compressors.zlib import ZlibCompressor
from expanse.encryption.encryptor import Encryptor
from expanse.encryption.errors import DecryptionError
from expanse.encryption.key import Key
from expanse.encryption.key_chain import KeyChain
from expanse.encryption.message import Message


SECRET = b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb"
SECRET2 = b"MG6cMKYU4q3UTine3OT-UiPX-Zp-Ga10"
SALT = b"73NBdlFeA2L1rP-GDasaIFOKYZMIWo07"


@pytest.fixture
def key_chain() -> KeyChain:
    return KeyChain([Key(SECRET)])


@pytest.fixture
def encryptor(key_chain: KeyChain) -> Encryptor:
    return Encryptor(key_chain, SALT)


@pytest.fixture
def encryptor_without_compression(key_chain: KeyChain) -> Encryptor:
    return Encryptor(key_chain, SALT, compress=False)


@pytest.fixture
def encryptor_without_derivation(key_chain: KeyChain) -> Encryptor:
    return Encryptor(key_chain, SALT, derive=False)


def test_encryptor_can_encrypt_data(
    encryptor: Encryptor, mocker: MockerFixture
) -> None:
    compress = mocker.spy(ZlibCompressor, "compress")

    assert encryptor.has_compression()
    assert encryptor.has_derivation()

    message = encryptor.encrypt("Hello, World!")

    assert isinstance(message, Message)
    assert isinstance(message.payload, bytes)
    assert "iv" in message.headers
    assert "at" in message.headers
    assert message.headers["z"] == 1

    assert compress.call_count == 1


def test_encryptor_can_encrypt_data_without_compression(
    encryptor_without_compression: Encryptor, mocker: MockerFixture
) -> None:
    assert not encryptor_without_compression.has_compression()
    assert encryptor_without_compression.has_derivation()

    compress = mocker.spy(ZlibCompressor, "compress")

    message = encryptor_without_compression.encrypt("Hello, World!")

    assert isinstance(message, Message)
    assert isinstance(message.payload, bytes)
    assert "iv" in message.headers
    assert "at" in message.headers
    assert "z" not in message.headers

    assert compress.call_count == 0


def test_encryptor_can_decrypt_messages(
    encryptor: Encryptor, mocker: MockerFixture
) -> None:
    decompress = mocker.spy(ZlibCompressor, "decompress")

    message = encryptor.encrypt("Hello, World!")

    decrypted = encryptor.decrypt(message)

    assert decrypted == "Hello, World!"

    assert decompress.call_count == 1


def test_encryptor_can_decrypt_data_without_compression(
    encryptor_without_compression: Encryptor, mocker: MockerFixture
) -> None:
    decompress = mocker.spy(ZlibCompressor, "decompress")

    message = encryptor_without_compression.encrypt("Hello, World!")

    decrypted = encryptor_without_compression.decrypt(message)

    assert decrypted == "Hello, World!"

    assert decompress.call_count == 0


def test_encryptor_can_generate_keys() -> None:
    key = Encryptor.generate_random_key()

    assert isinstance(key, bytes)
    assert len(key) == 32


def test_encryptor_iterates_over_keys_to_decrypt() -> None:
    key_chain = KeyChain([Key(SECRET2)])
    encryptor = Encryptor(key_chain, SALT)

    message = encryptor.encrypt("Hello, World!")

    key_chain = KeyChain([Key(SECRET), Key(SECRET2)])
    encryptor = Encryptor(key_chain, SALT)

    decrypted = encryptor.decrypt(message)

    assert decrypted == "Hello, World!"


def test_encryptor_raises_an_error_if_it_can_not_decrypt_message() -> None:
    key_chain = KeyChain([Key(SECRET2)])
    encryptor = Encryptor(key_chain, SALT)

    message = encryptor.encrypt("Hello, World!")

    key_chain = KeyChain([Key(SECRET)])
    encryptor = Encryptor(key_chain, SALT)

    with pytest.raises(DecryptionError):
        encryptor.decrypt(message)


def test_encryptor_can_be_used_without_key_derivation(
    encryptor_without_derivation: Encryptor,
) -> None:
    assert not encryptor_without_derivation.has_derivation()

    message = encryptor_without_derivation.encrypt("Hello, World!")

    decrypted = encryptor_without_derivation.decrypt(message)

    assert decrypted == "Hello, World!"
