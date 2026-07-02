from __future__ import annotations


_REDACTED = "[redacted]"


class Secret[T]:
    __slots__ = ("__value",)

    def __init__(self, value: T) -> None:
        self.__value: T = value

    def reveal(self) -> T:
        return self.__value

    def __repr__(self):
        return f"{self.__class__.__name__}({_REDACTED!r})"

    def __str__(self) -> str:
        return _REDACTED

    def __eq__(self, other: Secret) -> bool:
        if not isinstance(other, Secret):
            return NotImplemented

        return self.__value == other.reveal()
