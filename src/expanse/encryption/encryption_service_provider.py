import base64

from pathlib import Path
from typing import TYPE_CHECKING

from expanse.core.application import Application
from expanse.encryption.errors import MissingSecretKeyError
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.core.console.gateway import Gateway
    from expanse.encryption.encryptor import Encryptor


class EncryptionServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.encryption.encryptor import Encryptor

        self._container.singleton(Encryptor, self._create_encryptor)

    async def boot(self) -> None:
        from expanse.core.console.gateway import Gateway

        await self._container.on_resolved(Gateway, self._register_command_path)

    async def _create_encryptor(self, app: Application) -> "Encryptor":
        from expanse.encryption.encryptor import Cipher
        from expanse.encryption.encryptor import Encryptor
        from expanse.encryption.key import Key
        from expanse.encryption.key_chain import KeyChain

        secret_key: str = app.config.get("app.secret_key")
        previous_keys: str = app.config.get("app.previous_keys")
        cipher: str = app.config.get("encryption.cipher")
        salt: str = app.config.get("encryption.salt")

        key_chain = KeyChain([Key(self._normalize_key(secret_key))])

        if previous_keys:
            for key in previous_keys.split(","):
                key = key.strip()

                if not key:
                    continue

                key_chain.add(Key(self._normalize_key(key)))

        return Encryptor(
            key_chain,
            self._normalize_key(salt),
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
