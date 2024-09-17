import secrets

from enum import StrEnum
from typing import Any
from typing import ClassVar


class Cipher(StrEnum):
    AES_256_GCM: str = "aes-256-gcm"


class Encryptor:
    CIPHERS: ClassVar[dict[Cipher, dict[str, Any]]] = {
        Cipher.AES_256_GCM: {"key_length": 32, "iv_length": 16}
    }

    def __init__(self, secret_key: bytes, cipher: Cipher = Cipher.AES_256_GCM) -> None:
        self._secret_key = secret_key
        self._cipher = cipher

    @classmethod
    def generate_random_key(cls, cipher: Cipher = Cipher.AES_256_GCM) -> bytes:
        cipher_config = cls.CIPHERS[cipher]
        key = secrets.token_bytes(cipher_config["key_length"])

        return key
