from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.encryption.errors import DecryptionError


if TYPE_CHECKING:
    from expanse.encryption.ciphers.base_cipher import BaseCipher
    from expanse.encryption.message import Message


class Cipher:
    def __init__(self, cipher_class: type[BaseCipher] | None = None) -> None:
        if cipher_class is None:
            from expanse.encryption.ciphers.aes256_gcm import AES256GCMCipher

            cipher_class = AES256GCMCipher

        self._cipher_class: type[BaseCipher] = cipher_class
        self.key_length: int = cipher_class.key_length
        self.iv_length: int = cipher_class.iv_length

    def encrypt(
        self, clear_text: str, key: bytes, deterministic: bool = False
    ) -> Message:
        return self._cipher_class(key, deterministic=deterministic).encrypt(clear_text)

    def decrypt(self, encrypted_message: Message, key: bytes | list[bytes]) -> str:
        keys: list[bytes] = [key] if isinstance(key, bytes) else key

        return self._try_to_decrypt_with_keys(encrypted_message, keys)

    def _try_to_decrypt_with_keys(
        self, encrypted_message: Message, keys: list[bytes]
    ) -> str:
        for i, key in enumerate(keys):
            try:
                return self._cipher_class(key).decrypt(encrypted_message)
            except DecryptionError:
                if i == len(keys) - 1:
                    raise
