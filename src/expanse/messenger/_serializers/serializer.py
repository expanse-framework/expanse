from abc import ABC
from abc import abstractmethod
from importlib import import_module

from expanse.types.messenger import Encoded


class Serializer[T](ABC):
    name: str

    @abstractmethod
    def encode(self, obj: T) -> Encoded: ...

    @abstractmethod
    def decode(self, data: Encoded) -> T: ...

    @abstractmethod
    def supports(self, obj: T | Encoded) -> bool: ...

    def _import_type(self, type_: str) -> type[T]:
        module_name, class_name = type_.rsplit(".", 1)
        module = import_module(module_name)
        return getattr(module, class_name)

    def _get_type(self, data: type[T]) -> str:
        return f"{data.__module__}.{data.__name__}"
