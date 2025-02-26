import base64

from typing import TYPE_CHECKING

from expanse.core.application import Application


if TYPE_CHECKING:
    from expanse.encryption.encryptor import Encryptor


class EncryptorFactory:
    def __init__(self, app: Application) -> None:
        self._app = app

    def make(self, compress: bool = True, derive: bool = True) -> "Encryptor":
        from expanse.encryption.encryptor import Cipher
        from expanse.encryption.encryptor import Encryptor
        from expanse.encryption.key import Key
        from expanse.encryption.key_chain import KeyChain

        secret_key: str | SecretStr = self._app.config.get("app.secret_key")
        previous_keys: str | SecretStr = self._app.config.get("app.previous_keys")
        cipher: str = self._app.config.get("encryption.cipher")
        salt: str | SecretStr = self._app.config.get("encryption.salt")

        key_chain = KeyChain([Key(self._normalize_key(secret_key))])

        if isinstance(previous_keys, SecretStr):
            previous_keys = previous_keys.get_secret_value()

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
            compress=compress,
            derive=derive,
        )

    def _normalize_key(self, key: str) -> bytes:
        from expanse.encryption.errors import MissingSecretKeyError

        if not key:
            raise MissingSecretKeyError()

        if isinstance(key, SecretStr):
            key = key.get_secret_value()

        if key.startswith("base64:"):
            return base64.urlsafe_b64decode(key[7:])

        return key.encode()
