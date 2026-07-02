from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from expanse.encryption.key import Key
from expanse.support.secret import Secret


_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@$%&*-_+"


class KeyGenerator:
    def __init__(
        self, salt: Secret[bytes] | None = None, label: bytes | None = None
    ) -> None:
        self._salt: Secret[bytes] | None = salt
        self._label: bytes | None = label

    def generate_key(self, secret_key: Key, key_size: int = 32) -> Key:
        kdf = HKDF(
            algorithm=hashes.SHA384(),
            length=key_size,
            salt=self._salt.reveal() if self._salt is not None else None,
            info=self._label,
        )

        return Key(kdf.derive(secret_key.value.reveal()))
