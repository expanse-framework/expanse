import pytest

from expanse.core.application import Application
from expanse.encryption.encryptor_factory import EncryptorFactory
from expanse.encryption.errors import DecryptionError
from expanse.encryption.errors import InvalidSecretKeyError


@pytest.fixture
def factory(app: Application) -> EncryptorFactory:
    app.config["app.secret_key"] = "base64:uwyDt6Sezpoa84jCLhvWuLG878Gz3RJvA2_VsNql5EY="
    app.config["app.previous_keys"] = "MG6cMKYU4q3UTine3OT-UiPX-Zp-Ga10"
    app.config["encryption.salt"] = "73NBdlFeA2L1rP-GDasaIFOKYZMIWo07"

    return EncryptorFactory(app)


def test_encryptor_factory_can_create_encryptor(factory: EncryptorFactory) -> None:
    encryptor = factory.make()

    assert encryptor.has_compression()


def test_encryptor_factory_can_create_encryptor_without_compression(
    factory: EncryptorFactory,
) -> None:
    encryptor = factory.make(compress=False)

    assert not encryptor.has_compression()


@pytest.mark.parametrize(
    "secret_key",
    [
        "tooshort",
        "base64:dG9vc2hvcnQ=",
    ],
)
def test_encryptor_factory_rejects_keys_shorter_than_32_bytes(
    factory: EncryptorFactory, app: Application, secret_key: str
) -> None:
    app.config["app.secret_key"] = secret_key

    with pytest.raises(InvalidSecretKeyError):
        factory.make()


def test_encryptor_factory_splits_comma_separated_previous_keys(
    factory: EncryptorFactory, app: Application
) -> None:
    app.config["app.previous_keys"] = (
        "MG6cMKYU4q3UTine3OT-UiPX-Zp-Ga10,ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb"
    )

    encryptor = factory.make()

    assert len(encryptor._key_chain) == 3


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
