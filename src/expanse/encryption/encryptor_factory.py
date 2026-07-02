import base64

from typing import TYPE_CHECKING

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

        secret_key: Secret[str] = Secret[str].wrap(
            self._app.config.get("app.secret_key")
        )
        previous_keys: list[str | Secret[str]] = self._app.config.get(
            "app.previous_keys"
        )
        cipher: str = self._app.config.get("encryption.cipher")
        salt: Secret[str] = Secret[str].wrap(self._app.config.get("encryption.salt"))

        key_chain = KeyChain([Key(self._normalize_key(secret_key))])

        if previous_keys:
            for raw_key in previous_keys:
                key = Secret.wrap(raw_key)

                if not key:
                    continue

                key_chain.add(Key(self._normalize_key(key)))

        return Encryptor(
            key_chain,
            KeyGenerator(self._normalize_key(salt), label=label),
            Cipher(cipher),
            compress=compress,
        )

    def _normalize_key(self, key: Secret[str]) -> Secret[bytes]:
        from expanse.encryption.errors import MissingSecretKeyError

        if not key.reveal():
            raise MissingSecretKeyError()

        if key.reveal().startswith("base64:"):
            return Secret(base64.urlsafe_b64decode(key.reveal()[7:]))

        return Secret(key.reveal().encode())
