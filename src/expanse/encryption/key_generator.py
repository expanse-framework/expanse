from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from expanse.encryption.key import Key


class KeyGenerator:
    def __init__(self, salt: bytes | None = None, label: bytes | None = None) -> None:
        self._salt: bytes | None = salt
        self._label: bytes | None = label

    def generate_key(self, secret_key: Key, key_size: int = 32) -> Key:
        kdf = HKDF(
            algorithm=hashes.SHA384(),
            length=key_size,
            salt=self._salt,
            info=self._label,
        )

        return Key(kdf.derive(secret_key.value))
