from __future__ import annotations

import secrets

from typing import TYPE_CHECKING
from typing import Any
from typing import get_args
from typing import overload
from typing import override

from pydantic_core import CoreSchema
from pydantic_core import core_schema


if TYPE_CHECKING:
    from pydantic import GetCoreSchemaHandler


_REDACTED = "[redacted]"


class SecretError(Exception):
    """
    Base class for all secret-related errors.
    """


class Secret[T]:
    __slots__ = ("__value",)

    def __init__(self, value: T) -> None:
        self.__value: T = value

    @overload
    @classmethod
    def wrap(cls, value: T) -> Secret[T]: ...

    @overload
    @classmethod
    def wrap(cls, value: Secret[T]) -> Secret[T]: ...

    @classmethod
    def wrap(cls, value: T | Secret[T]) -> Secret[T]:
        if value is None:
            raise SecretError("Secret value cannot be None")

        if isinstance(value, Secret):
            return value

        return cls(value)

    def reveal(self) -> T:
        return self.__value

    @override
    def __repr__(self):
        if isinstance(self.__value, str):
            return f"{self.__class__.__name__}({_REDACTED!r})"
        elif isinstance(self.__value, bytes):
            return f"{self.__class__.__name__}({_REDACTED.encode()!r})"

        return f"{self.__class__.__name__}[{type(self.__value).__name__}]()"

    @override
    def __str__(self) -> str:
        return _REDACTED

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Secret):
            return NotImplemented

        other_value = other.reveal()
        if (
            not isinstance(self.__value, (str, bytes))
            or not isinstance(other_value, (str, bytes))
            or type(self.__value) is not type(other_value)
        ):
            return self.__value == other_value

        return secrets.compare_digest(self.__value, other_value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        instance_schema = core_schema.is_instance_schema(cls)
        args = get_args(source)
        schema = handler.generate_schema(args[0])
        non_instance_schema = core_schema.no_info_after_validator_function(
            Secret[args[0]].wrap, schema
        )
        return core_schema.union_schema([instance_schema, non_instance_schema])
