import base64

from typing import TYPE_CHECKING

from expanse.contracts.encryption.encryptor_factory import (
    EncryptorFactory as EncryptorFactoryContract,
)
from expanse.core.application import Application
from expanse.support.secret import Secret


if TYPE_CHECKING:
    from expanse.encryption.encryptor import Encryptor


class EncryptorFactory(EncryptorFactoryContract):
    MIN_KEY_LENGTH: int = 32

    def __init__(self, app: Application) -> None:
        self._app = app

    def make(self, compress: bool = True, purpose: bytes | None = None) -> "Encryptor":
        from expanse.encryption.encryptor import Cipher
        from expanse.encryption.encryptor import Encryptor
        from expanse.encryption.key import Key
        from expanse.encryption.key_chain import KeyChain

        secret_key: Secret[str] = Secret[str].wrap(
            self._app.config.get("app.secret_key")
        )
        previous_keys: str | Secret[str] | list[str | Secret[str]] | None = (
            self._app.config.get("app.previous_keys")
        )
        cipher: str = self._app.config.get("encryption.cipher")
        salt: Secret[str] = Secret[str].wrap(self._app.config.get("encryption.salt"))

        key_chain = KeyChain([Key(self._normalize_key(secret_key))])

        if previous_keys:
            raw_keys: list[str | Secret[str]]
            if isinstance(previous_keys, str | Secret):
                raw_keys = list(Secret[str].wrap(previous_keys).reveal().split(","))
            else:
                raw_keys = previous_keys

            for raw_key in raw_keys:
                key = Secret[str].wrap(raw_key).reveal().strip()

                if not key:
                    continue

                key_chain.add(Key(self._normalize_key(Secret(key))))

        return Encryptor(
            key_chain,
            Cipher(cipher),
            salt=self._normalize_key(salt),
            purpose=purpose,
            compress=compress,
            store_key_references=self._app.config.get(
                "encryption.store_key_references", False
            ),
        )

    def _normalize_key(self, key: Secret[str]) -> Secret[bytes]:
        from expanse.encryption.errors import InvalidSecretKeyError
        from expanse.encryption.errors import MissingSecretKeyError

        if not key.reveal():
            raise MissingSecretKeyError()

        if key.reveal().startswith("base64:"):
            normalized = base64.urlsafe_b64decode(key.reveal()[7:])
        else:
            normalized = key.reveal().encode()

        # HKDF stretches short keys to the cipher's key size but adds no entropy,
        # so weak keys must be rejected outright.
        if len(normalized) < self.MIN_KEY_LENGTH:
            raise InvalidSecretKeyError()

        return Secret(normalized)
