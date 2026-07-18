from __future__ import annotations

import hmac

from expanse.encryption.ciphers.base_cipher import BaseCipher
from expanse.encryption.errors import DecryptionError
from expanse.encryption.message import Message


class AES256GCMCipher(BaseCipher):
    key_length: int = 32
    iv_length: int = 12

    def encrypt(self, data: bytes, *, additional_data: bytes | None = None) -> Message:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.ciphers import Cipher
        from cryptography.hazmat.primitives.ciphers.algorithms import AES
        from cryptography.hazmat.primitives.ciphers.modes import GCM

        iv = self._generate_iv(data)
        cipher = Cipher(AES(self._secret.reveal()), GCM(iv), backend=default_backend())

        encryptor = cipher.encryptor()
        if additional_data is not None:
            encryptor.authenticate_additional_data(additional_data)

        encrypted = encryptor.update(data) + encryptor.finalize()

        message = Message(encrypted)
        message.headers.update({"iv": iv, "at": encryptor.tag})

        return message

    def decrypt(
        self, message: Message, *, additional_data: bytes | None = None
    ) -> bytes:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.ciphers import Cipher
        from cryptography.hazmat.primitives.ciphers.algorithms import AES
        from cryptography.hazmat.primitives.ciphers.modes import GCM

        encrypted_data = message.payload
        iv = message.headers.get("iv")
        auth_tag = message.headers.get("at")

        if not isinstance(auth_tag, bytes) or len(auth_tag) != 16:
            raise DecryptionError("Invalid tag")

        if not isinstance(iv, bytes) or len(iv) != self.iv_length:
            raise DecryptionError("Invalid initialization vector")

        cipher = Cipher(AES(self._secret.reveal()), GCM(iv), backend=default_backend())

        decryptor = cipher.decryptor()

        if additional_data is not None:
            decryptor.authenticate_additional_data(additional_data)

        try:
            decrypted = decryptor.update(encrypted_data) + decryptor.finalize_with_tag(
                auth_tag
            )
        except Exception as e:
            raise DecryptionError("Unable to decrypt message") from e

        return decrypted

    def _generate_iv(self, data: bytes) -> bytes:
        return hmac.digest(self._secret.reveal(), data, "sha256")[: self.iv_length]
