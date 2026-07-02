import hashlib

from expanse.support.secret import Secret


class Key:
    def __init__(self, value: bytes | Secret[bytes]):
        if isinstance(value, bytes):
            value = Secret(value)

        self._value: Secret[bytes] = value

    @property
    def id(self) -> str:
        return hashlib.sha1(self._value.reveal()).hexdigest()[:4]

    @property
    def value(self) -> Secret[bytes]:
        return self._value
