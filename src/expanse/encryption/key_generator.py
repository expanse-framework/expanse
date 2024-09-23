import hashlib


class KeyGenerator:
    def __init__(self, secret: bytes, iterations: int | None = None) -> None:
        self._secret = secret
        self._iterations = iterations

    def generate_key(self, salt: bytes, key_size: int = 32) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256", self._secret, salt, self._iterations or 2**16, dklen=key_size
        )
