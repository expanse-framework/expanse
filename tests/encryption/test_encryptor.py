import pytest

from pytest_mock import MockerFixture

from expanse.encryption.compressors.zlib import ZlibCompressor
from expanse.encryption.encryptor import Encryptor
from expanse.encryption.errors import DecryptionError
from expanse.encryption.key import Key
from expanse.encryption.key_chain import KeyChain
from expanse.encryption.key_generator import KeyGenerator
from expanse.encryption.message import Message


SECRET = b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb"
SECRET2 = b"MG6cMKYU4q3UTine3OT-UiPX-Zp-Ga10"
SALT = b"73NBdlFeA2L1rP-GDasaIFOKYZMIWo07"


@pytest.fixture
def key_chain() -> KeyChain:
    return KeyChain([Key(SECRET)])


@pytest.fixture
def key_generator() -> KeyGenerator:
    return KeyGenerator(SALT)


@pytest.fixture
def encryptor(key_chain: KeyChain, key_generator: KeyGenerator) -> Encryptor:
    return Encryptor(key_chain, key_generator)


@pytest.fixture
def encryptor_without_compression(
    key_chain: KeyChain, key_generator: KeyGenerator
) -> Encryptor:
    return Encryptor(key_chain, key_generator, compress=False)


def test_encryptor_can_encrypt_data(
    encryptor: Encryptor, mocker: MockerFixture
) -> None:
    compress = mocker.spy(ZlibCompressor, "compress")

    assert encryptor.has_compression()

    encrypted_string = encryptor.encrypt("Hello, World!")
    message = encryptor.encrypt_raw("Hello, World!")

    assert isinstance(encrypted_string, str)
    assert isinstance(message, Message)
    assert isinstance(message.payload, bytes)
    assert "iv" in message.headers
    assert "at" in message.headers
    assert message.headers["z"] == 1

    assert compress.call_count == 2


def test_encryptor_can_encrypt_data_without_compression(
    encryptor_without_compression: Encryptor, mocker: MockerFixture
) -> None:
    assert not encryptor_without_compression.has_compression()

    compress = mocker.spy(ZlibCompressor, "compress")

    encrypted_string = encryptor_without_compression.encrypt("Hello, World!")
    message = encryptor_without_compression.encrypt_raw("Hello, World!")

    assert isinstance(encrypted_string, str)
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

    encrypted_string = encryptor.encrypt("Hello, World!")

    decrypted = encryptor.decrypt(encrypted_string)

    assert decrypted == "Hello, World!"

    assert decompress.call_count == 1


def test_encryptor_can_decrypt_data_without_compression(
    encryptor_without_compression: Encryptor, mocker: MockerFixture
) -> None:
    decompress = mocker.spy(ZlibCompressor, "decompress")

    encrypted_string = encryptor_without_compression.encrypt("Hello, World!")

    decrypted = encryptor_without_compression.decrypt(encrypted_string)

    assert decrypted == "Hello, World!"

    assert decompress.call_count == 0


def test_encryptor_can_decrypt_string_messages(encryptor: Encryptor) -> None:
    encrypted_string = encryptor.encrypt("Hello, World!")

    decrypted = encryptor.decrypt(encrypted_string)

    assert decrypted == "Hello, World!"


def test_encryptor_can_generate_keys() -> None:
    key = Encryptor.generate_random_key()

    assert isinstance(key, bytes)
    assert len(key) == 32


def test_encryptor_iterates_over_keys_to_decrypt(key_generator: KeyGenerator) -> None:
    key_chain = KeyChain([Key(SECRET2)])
    encryptor = Encryptor(key_chain, key_generator)

    encrypted_string = encryptor.encrypt("Hello, World!")

    key_chain = KeyChain([Key(SECRET), Key(SECRET2)])
    encryptor = Encryptor(key_chain, key_generator)

    decrypted = encryptor.decrypt(encrypted_string)

    assert decrypted == "Hello, World!"


def test_encryptor_raises_an_error_if_it_can_not_decrypt_message(
    key_generator: KeyGenerator,
) -> None:
    key_chain = KeyChain([Key(SECRET2)])
    encryptor = Encryptor(key_chain, key_generator)

    encrypted_string = encryptor.encrypt("Hello, World!")

    key_chain = KeyChain([Key(SECRET)])
    encryptor = Encryptor(key_chain, key_generator)

    with pytest.raises(DecryptionError):
        encryptor.decrypt(encrypted_string)
