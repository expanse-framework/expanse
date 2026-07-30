from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from expanse.encryption.key import Key
from expanse.support.secret import Secret


_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@$%&*-_+"


class KeyGenerator:
    @classmethod
    def generate_key(
        cls,
        secret_key: Key,
        key_size: int = 32,
        *,
        salt: Secret[bytes] | bytes | None = None,
        purpose: bytes | str | None = None,
    ) -> Key:
        if isinstance(purpose, str):
            purpose = purpose.encode()

        kdf = HKDF(
            algorithm=hashes.SHA384(),
            length=key_size,
            salt=Secret[bytes].wrap(salt).reveal() if salt is not None else None,
            info=purpose,
        )

        return Key(kdf.derive(secret_key.value.reveal()))
