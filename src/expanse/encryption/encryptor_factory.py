import base64

from typing import TYPE_CHECKING

from pydantic import SecretStr

from expanse.core.application import Application
from expanse.encryption.key_generator import KeyGenerator
from expanse.support.secret import Secret


if TYPE_CHECKING:
    from expanse.encryption.encryptor import Encryptor


class EncryptorFactory:
    def __init__(self, app: Application) -> None:
        self._app = app

    def make(self, compress: bool = True, label: bytes | None = None) -> "Encryptor":
        from expanse.encryption.encryptor import Cipher
        from expanse.encryption.encryptor import Encryptor
        from expanse.encryption.key import Key
        from expanse.encryption.key_chain import KeyChain

        secret_key: str = self._app.config.get("app.secret_key", raw=True)
        previous_keys: list[str | SecretStr] = self._app.config.get("app.previous_keys")
        cipher: str = self._app.config.get("encryption.cipher")
        salt: str = self._app.config.get("encryption.salt", raw=True)

        key_chain = KeyChain([Key(Secret(self._normalize_key(secret_key)))])

        if previous_keys:
            for key in previous_keys:
                if isinstance(key, SecretStr):
                    key = key.get_secret_value()

                key = key.strip()

                if not key:
                    continue

                key_chain.add(Key(self._normalize_key(key)))

        return Encryptor(
            key_chain,
            KeyGenerator(Secret(self._normalize_key(salt)), label=label),
            Cipher(cipher),
            compress=compress,
        )

    def _normalize_key(self, key: str) -> bytes:
        from expanse.encryption.errors import MissingSecretKeyError

        if not key:
            raise MissingSecretKeyError()

        if key.startswith("base64:"):
            return base64.urlsafe_b64decode(key[7:])

        return key.encode()
