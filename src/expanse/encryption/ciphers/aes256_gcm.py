from __future__ import annotations

import hmac
import secrets

from expanse.encryption.ciphers.base_cipher import BaseCipher
from expanse.encryption.errors import DecryptionError
from expanse.encryption.message import Message


class AES256GCMCipher(BaseCipher):
    key_length: int = 32
    iv_length: int = 12

    def encrypt(self, data: bytes) -> Message:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.ciphers import Cipher
        from cryptography.hazmat.primitives.ciphers.algorithms import AES
        from cryptography.hazmat.primitives.ciphers.modes import GCM

        iv = self._generate_iv(data)
        cipher = Cipher(AES(self._secret), GCM(iv), backend=default_backend())

        encryptor = cipher.encryptor()
        encrypted = encryptor.update(data) + encryptor.finalize()

        message = Message(encrypted)
        message.headers.update({"iv": iv, "at": encryptor.tag})

        return message

    def decrypt(self, message: Message) -> bytes:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.ciphers import Cipher
        from cryptography.hazmat.primitives.ciphers.algorithms import AES
        from cryptography.hazmat.primitives.ciphers.modes import GCM

        encrypted_data = message.payload
        iv = message.headers["iv"]
        auth_tag = message.headers["at"]

        if not auth_tag or len(auth_tag) != 16:
            raise DecryptionError("Invalid tag")

        cipher = Cipher(AES(self._secret), GCM(iv), backend=default_backend())

        decryptor = cipher.decryptor()

        try:
            decrypted = decryptor.update(encrypted_data) + decryptor.finalize_with_tag(
                auth_tag
            )
        except Exception as e:
            raise DecryptionError("Unable to decrypt message") from e

        return decrypted

    def _generate_iv(self, data: bytes) -> bytes:
        if not self._deterministic:
            return secrets.token_bytes(self.iv_length)

        return hmac.digest(self._secret, data, "sha256")[: self.iv_length]
