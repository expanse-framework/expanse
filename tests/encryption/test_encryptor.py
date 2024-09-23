from pytest_mock import MockerFixture

from expanse.encryption.compressors.zlib import ZlibCompressor
from expanse.encryption.encryptor import Encryptor
from expanse.encryption.message import Message


SECRET = b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb"
SALT = b"73NBdlFeA2L1rP-GDasaIFOKYZMIWo07"


def test_encryptor_can_encrypt_data(mocker: MockerFixture) -> None:
    encryptor = Encryptor(SECRET, SALT)

    compress = mocker.spy(ZlibCompressor, "compress")

    message = encryptor.encrypt("Hello, World!")

    assert isinstance(message, Message)
    assert isinstance(message.payload, bytes)
    assert "iv" in message.headers
    assert "at" in message.headers
    assert message.headers["compressed"]

    assert compress.call_count == 1


def test_encryptor_can_encrypt_data_without_compression(mocker: MockerFixture) -> None:
    encryptor = Encryptor(SECRET, SALT, compress=False)

    compress = mocker.spy(ZlibCompressor, "compress")

    message = encryptor.encrypt("Hello, World!")

    assert isinstance(message, Message)
    assert isinstance(message.payload, bytes)
    assert "iv" in message.headers
    assert "at" in message.headers
    assert "compressed" not in message.headers

    assert compress.call_count == 0


def test_encryptor_can_decrypt_messages(mocker: MockerFixture) -> None:
    encryptor = Encryptor(SECRET, SALT)

    decompress = mocker.spy(ZlibCompressor, "decompress")

    message = encryptor.encrypt("Hello, World!")

    decrypted = encryptor.decrypt(message)

    assert decrypted == "Hello, World!"

    assert decompress.call_count == 1


def test_encryptor_can_decrypt_data_without_compression(mocker: MockerFixture) -> None:
    encryptor = Encryptor(SECRET, SALT, compress=False)

    decompress = mocker.spy(ZlibCompressor, "decompress")

    message = encryptor.encrypt("Hello, World!")

    decrypted = encryptor.decrypt(message)

    assert decrypted == "Hello, World!"

    assert decompress.call_count == 0


def test_encryptor_can_encrypt_and_decrypt_data_deterministically() -> None:
    encryptor = Encryptor(SECRET, SALT)

    message = encryptor.encrypt("Hello, World!", deterministic=True)
    message2 = encryptor.encrypt("Hello, World!", deterministic=True)

    assert message.payload == message2.payload

    decrypted = encryptor.decrypt(message)
    decrypted2 = encryptor.decrypt(message2)

    assert decrypted == "Hello, World!"
    assert decrypted2 == "Hello, World!"


def test_encryptor_can_generate_keys() -> None:
    key = Encryptor.generate_random_key()

    assert isinstance(key, bytes)
    assert len(key) == 32
