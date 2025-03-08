import hashlib


class Key:
    def __init__(self, value: bytes):
        self._value = value

    @property
    def id(self) -> str:
        return hashlib.sha1(self._value).hexdigest()[:4]

    @property
    def value(self) -> bytes:
        return self._value
