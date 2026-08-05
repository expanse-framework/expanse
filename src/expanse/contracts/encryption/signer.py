from abc import ABC
from abc import abstractmethod


class Signer(ABC):
    @abstractmethod
    def sign(
        self,
        data: bytes | str,
        purpose: bytes | str | None = None,
    ) -> bytes: ...

    @abstractmethod
    def verify(
        self, data: bytes, signature: bytes, purpose: bytes | str | None = None
    ) -> bool: ...
