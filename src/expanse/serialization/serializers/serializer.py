from abc import ABC
from abc import abstractmethod
from typing import Any

from expanse.types.serialization import Encoded


class Serializer[T](ABC):
    name: str

    @abstractmethod
    def encode(self, obj: T) -> Encoded: ...

    @abstractmethod
    def decode(self, data: Encoded) -> T: ...

    @abstractmethod
    def supports(self, obj: Any) -> bool: ...
