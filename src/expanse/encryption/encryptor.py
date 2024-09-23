import secrets

from enum import Enum
from typing import ClassVar

from expanse.encryption.ciphers.aes256_gcm import AES256GCMCipher
from expanse.encryption.ciphers.base_cipher import BaseCipher
from expanse.encryption.key_generator import KeyGenerator


class Cipher(Enum):
    AES_256_GCM: str = "aes-256-gcm"


class Encryptor:
    CIPHERS: ClassVar[dict[Cipher, BaseCipher]] = {Cipher.AES_256_GCM: AES256GCMCipher}

    def __init__(
        self, secret_key: bytes, salt: bytes, cipher: Cipher = Cipher.AES_256_GCM
    ) -> None:
        self._secret_key = secret_key
        self._salt = salt
        self._cipher = cipher

    @classmethod
    def generate_random_key(cls, cipher: Cipher = Cipher.AES_256_GCM) -> bytes:
        cipher_class = cls.CIPHERS[cipher]
        key = secrets.token_bytes(cipher_class.key_length)

        return key

    def derive_key(self, iterations: int | None = None, length: int = 64) -> bytes:
        return KeyGenerator(self._secret_key, iterations=iterations).generate_key(
            self._salt, length=length
        )
