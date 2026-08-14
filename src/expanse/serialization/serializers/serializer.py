from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Self


class Serializer[T](ABC):
    name: str

    def __init__(self) -> None:
        self._restricted: bool = False
        self._allowed_types: set[str] = set()

    @abstractmethod
    def encode(self, obj: T) -> bytes:
        """
        Encode an object into a serialized format.

        :param obj: The object to be serialized.
        :return: The serialized data as bytes.
        """

    @abstractmethod
    def decode(self, data: bytes) -> T:
        """
        Decode an unwrapped serialized data into an object.

        :param data: The serialized data as bytes.
        :return: The deserialized object.
        """

    @abstractmethod
    def supports(self, obj: Any) -> bool: ...

    def restrict(self, allowed_types: set[str]) -> Self:
        """
        Restrict the serializer to only allow certain types.

        :param allowed_types: A set of allowed type names.
        :return: A restricted serializer that only allows the specified types.
        """
        self._restricted = True
        self._allowed_types = allowed_types

        return self

    def is_allowed(self, type_: str) -> bool:
        """
        Check if the given type is allowed.

        :param type_: The type name to check.
        :return: True if the type is allowed, False otherwise.
        """
        if not self._restricted:
            return True

        return type_ in self._allowed_types
