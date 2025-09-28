import pytest

from expanse.core.application import Application
from expanse.encryption.encryptor_factory import EncryptorFactory


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
