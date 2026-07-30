import pytest

from expanse.encryption.encryptor_factory import EncryptorFactory
from expanse.encryption.errors import DecryptionError
from expanse.encryption.key import Key
from expanse.encryption.key_chain import KeyChain
from expanse.support.secret import Secret


@pytest.fixture
def factory() -> EncryptorFactory:
    return EncryptorFactory(
        KeyChain(
            [
                Key(b"27WZmLjo%B7cSGtU1Qsi9foE8x7Y_nWD"),
                Key(b"MG6cMKYU4q3UTine3OT-UiPX-Zp-Ga10"),
            ]
        ),
        salt=Secret(b"73NBdlFeA2L1rP-GDasaIFOKYZMIWo07"),
    )


def test_encryptor_factory_can_create_encryptor(factory: EncryptorFactory) -> None:
    encryptor = factory.make()

    assert encryptor.has_compression()


def test_encryptor_factory_can_create_encryptor_without_compression(
    factory: EncryptorFactory,
) -> None:
    encryptor = factory.make(compress=False)

    assert not encryptor.has_compression()


def test_encryptor_factory_can_create_encryptor_with_specific_labels(
    factory: EncryptorFactory,
) -> None:
    encryptor = factory.make(purpose=b"test-label")
    encryptor2 = factory.make(purpose=b"test-label-2")

    with pytest.raises(DecryptionError):
        encryptor.decrypt(encryptor2.encrypt("Hello, World!"))

    assert (
        encryptor.decrypt(factory.make(purpose=b"test-label").encrypt("Hello, World!"))
        == "Hello, World!"
    )
