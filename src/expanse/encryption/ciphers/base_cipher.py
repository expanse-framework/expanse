from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.encryption.message import Message


class BaseCipher(ABC):
    key_length: int
    iv_length: int

    def __init__(self, secret: bytes, deterministic: bool = False) -> None:
        self._secret = secret
        self._deterministic = deterministic

    @abstractmethod
    def encrypt(self, data: bytes) -> Message: ...

    @abstractmethod
    def decrypt(self, message: Message) -> bytes: ...
