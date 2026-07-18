from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.encryption.message import Message
    from expanse.support.secret import Secret


class BaseCipher(ABC):
    key_length: int
    iv_length: int

    def __init__(self, secret: Secret[bytes]) -> None:
        self._secret = secret

    @abstractmethod
    def encrypt(
        self, data: bytes, *, additional_data: bytes | None = None
    ) -> Message: ...

    @abstractmethod
    def decrypt(
        self, message: Message, *, additional_data: bytes | None = None
    ) -> bytes: ...
