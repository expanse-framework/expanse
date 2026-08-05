import base64

from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from expanse.contracts.encryption.signer import Signer as SignerContract
from expanse.core.application import Application
from expanse.encryption.key_chain import KeyChain
from expanse.support.secret import Secret
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.core.console.portal import Portal
    from expanse.encryption.encryptor_factory import EncryptorFactory


class EncryptionServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.contracts.encryption.encryptor_factory import (
            EncryptorFactory as EncryptorFactoryContract,
        )
        from expanse.encryption.encryption_manager import EncryptionManager

        self._container.singleton(KeyChain, self._build_key_chain)
        self._container.singleton(
            EncryptorFactoryContract, self._create_encryptor_factory
        )
        self._container.singleton(EncryptionManager)
        self._container.singleton(SignerContract, self._create_signer)

    async def boot(self) -> None:
        from expanse.core.console.portal import Portal

        await self._container.on_resolved(Portal, self._register_command_path)

    async def _build_key_chain(self, app: Application) -> KeyChain:
        from expanse.encryption.key import Key
        from expanse.encryption.key_chain import KeyChain

        secret_key: Secret[str] = Secret[str].wrap(
            cast("str", app.config.get("app.secret_key"))
        )
        previous_keys: str | Secret[str] | list[str | Secret[str]] | None = (
            app.config.get("app.previous_keys")
        )

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

        return key_chain

    def _create_encryptor_factory(
        self, key_chain: KeyChain, app: Application
    ) -> "EncryptorFactory":
        from expanse.encryption.encryptor import Cipher
        from expanse.encryption.encryptor_factory import EncryptorFactory

        raw_salt: Secret[str] | str | None = app.config.get("encryption.salt")
        if raw_salt is not None:
            raw_salt = Secret[str].wrap(raw_salt)

            salt = Secret[bytes].wrap(raw_salt.reveal().encode())
        else:
            salt = None

        return EncryptorFactory(
            key_chain,
            salt=salt,
            default_cipher=Cipher(app.config.get("encryption.cipher", "aes-256-gcm")),
            store_key_references=app.config.get(
                "encryption.store_key_references", False
            ),
        )

    def _create_signer(self, key_chain: KeyChain, app: Application) -> SignerContract:
        from expanse.encryption.signer import Signer

        raw_salt: Secret[str] | str | None = app.config.get("encryption.salt")
        if raw_salt is not None:
            raw_salt = Secret[str].wrap(raw_salt)

            salt = Secret[bytes].wrap(raw_salt.reveal().encode())
        else:
            salt = None

        return Signer(key_chain, salt=salt)

    async def _register_command_path(self, portal: "Portal") -> None:
        await portal.load_path(Path(__file__).parent.joinpath("console/commands"))

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
        if len(normalized) < 32:
            raise InvalidSecretKeyError()

        return Secret(normalized)
