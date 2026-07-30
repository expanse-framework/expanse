from typing import TYPE_CHECKING

from expanse.contracts.encryption.encryptor_factory import (
    EncryptorFactory as EncryptorFactoryContract,
)
from expanse.encryption.encryptor import Cipher
from expanse.encryption.key_chain import KeyChain
from expanse.support.secret import Secret


if TYPE_CHECKING:
    from expanse.encryption.encryptor import Encryptor


class EncryptorFactory(EncryptorFactoryContract):
    def __init__(
        self,
        key_chain: KeyChain,
        salt: Secret[bytes] | bytes | None = None,
        default_cipher: Cipher = Cipher.AES_256_GCM,
        store_key_references: bool = False,
    ) -> None:
        self._key_chain: KeyChain = key_chain
        self._salt: Secret[bytes] | bytes | None = (
            Secret[bytes].wrap(salt) if salt is not None else None
        )
        self._default_cipher: Cipher = default_cipher
        self._store_key_references: bool = store_key_references

    def make(self, compress: bool = True, purpose: bytes | None = None) -> "Encryptor":
        from expanse.encryption.encryptor import Encryptor

        return Encryptor(
            self._key_chain,
            self._default_cipher,
            salt=self._salt,
            purpose=purpose,
            compress=compress,
            store_key_references=self._store_key_references,
        )
