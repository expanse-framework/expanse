from expanse.contracts.encryption.encryptor import Encryptor
from expanse.core.application import Application
from expanse.encryption.encryption_service_provider import EncryptionServiceProvider
from expanse.encryption.encryptor_factory import EncryptorFactory


async def test_service_provider_registers_encryptor_factory_and_encryptor(
    app: Application,
) -> None:
    app.config["app.secret_key"] = "base64:V2h5IGFyZSB0aGUgY29tcGxleCB0aGF0Lg=="
    app.config["encryption.salt"] = "base64:MjAyMS0wNC0xNCAxNzowMTo1NQ=="
    provider = EncryptionServiceProvider(app.container)

    await provider.register()

    assert app.container.has(EncryptorFactory)
    assert app.container.has(Encryptor)

    encryptor = await app.container.get(Encryptor)

    assert isinstance(encryptor, Encryptor)
