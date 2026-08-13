import pickle

from collections import defaultdict
from importlib import import_module
from io import BytesIO
from typing import Any
from typing import Protocol
from typing import Self
from typing import override

from expanse.serialization.serializers.serializer import Serializer
from expanse.support._utils import class_to_name


class _ReadableFileobj(Protocol):
    def read(self, n: int, /) -> bytes: ...
    def readline(self) -> bytes: ...


class RestrictedUnpickler(pickle.Unpickler):
    def __init__(self, file: _ReadableFileobj, allow_list: dict[str, set[str]]) -> None:
        super().__init__(file)

        self._allow_list: dict[str, set[str]] = allow_list

    def find_class(self, module: str, name: str) -> Any:
        if module not in self._allow_list or name not in self._allow_list[module]:
            raise pickle.UnpicklingError(
                f"Class {module}.{name} is not allowed for unpickling"
            )

        return getattr(import_module(module), name)


class PickleSerializer(Serializer[Any]):
    """
    A serializer that uses Python's built-in `pickle` module for serialization and deserialization.

    Due to the inherent security risks associated with unpickling arbitrary data, this serializer is restricted by default.
    """

    name: str = "restricted_pickle"

    def __init__(self) -> None:
        super().__init__()

        self._restricted: bool = True
        self._unpickler_allow_list: dict[str, set[str]] = defaultdict(set)

    @override
    def encode(self, obj: Any) -> bytes:
        return pickle.dumps(obj)

    @override
    def decode(self, data: bytes) -> Any:
        return RestrictedUnpickler(
            file=BytesIO(data), allow_list=self._unpickler_allow_list
        ).load()

    @override
    def supports(self, obj: Any) -> bool:
        return class_to_name(obj.__class__) in self._allowed_types

    @override
    def restrict(self, allowed_types: set[str]) -> Self:
        super().restrict(allowed_types)

        for type_name in allowed_types:
            module_name, class_name = type_name.rsplit(".", 1)
            self._unpickler_allow_list[module_name].add(class_name)

        return self
