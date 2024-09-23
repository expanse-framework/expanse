from __future__ import annotations

import hmac
import secrets

from expanse.encryption.ciphers.base_cipher import BaseCipher
from expanse.encryption.errors import DecryptionError
from expanse.encryption.message import Message


class AES256GCMCipher(BaseCipher):
    key_length: int = 32
    iv_length: int = 12

    def encrypt(self, clear_text: str) -> Message:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.ciphers import Cipher
        from cryptography.hazmat.primitives.ciphers.algorithms import AES
        from cryptography.hazmat.primitives.ciphers.modes import GCM

        iv = self._generate_iv(clear_text)
        cipher = Cipher(AES(self._secret), GCM(iv), backend=default_backend())

        encryptor = cipher.encryptor()
        encrypted = encryptor.update(clear_text.encode()) + encryptor.finalize()

        message = Message(encrypted)
        message.headers.update({"iv": iv, "auth_tag": encryptor.tag})

        return message

    def decrypt(self, encrypted_message: Message) -> str:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.ciphers import Cipher
        from cryptography.hazmat.primitives.ciphers.algorithms import AES
        from cryptography.hazmat.primitives.ciphers.modes import GCM

        encrypted_data = encrypted_message.payload
        iv = encrypted_message.headers["iv"]
        auth_tag = encrypted_message.headers["auth_tag"]

        if not auth_tag or len(auth_tag) != 16:
            raise DecryptionError()

        cipher = Cipher(AES(self._secret), GCM(iv), backend=default_backend())
        cipher.auth_tag = auth_tag
        cipher.auth_data = ""

        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted_data) + decryptor.finalize_with_tag(
            auth_tag
        )

        return decrypted.decode()

    def _generate_iv(self, clear_text: str) -> bytes:
        if not self._deterministic:
            return secrets.token_bytes(self.iv_length)

        return hmac.digest(self._secret, clear_text.encode(), "sha256")[
               : self.iv_length
               ]
