import base64

from pathlib import Path
from typing import TYPE_CHECKING

from expanse.asynchronous.core.application import Application
from expanse.asynchronous.support.service_provider import ServiceProvider
from expanse.common.encryption.errors import MissingSecretKeyError


if TYPE_CHECKING:
    from expanse.asynchronous.core.console.gateway import Gateway
    from expanse.common.encryption.encryptor import Encryptor


class EncryptionServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.common.encryption.encryptor import Encryptor

        self._container.singleton(Encryptor, self._create_encryptor)

    async def boot(self) -> None:
        from expanse.asynchronous.core.console.gateway import Gateway

        await self._container.on_resolved(Gateway, self._register_command_path)

    async def _create_encryptor(self, app: Application) -> "Encryptor":
        from expanse.common.encryption.encryptor import Cipher
        from expanse.common.encryption.encryptor import Encryptor

        secret_key: str = app.config.get("app.secret_key")
        cipher: str = app.config.get("encryption.cipher")

        return Encryptor(
            self._normalize_key(secret_key),
            Cipher(cipher),
        )

    async def _register_command_path(self, gateway: "Gateway") -> None:
        await gateway.load_path(Path(__file__).parent.joinpath("console/commands"))

    def _normalize_key(self, key: str) -> bytes:
        if not key:
            raise MissingSecretKeyError()

        if key.startswith("base64:"):
            return base64.b64decode(key[7:])

        return key.encode()
