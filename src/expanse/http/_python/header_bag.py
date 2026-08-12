from collections.abc import Mapping
from collections.abc import MutableMapping
from typing import Literal
from typing import TypeVar
from typing import overload


T = TypeVar("T")


class HeaderBag(MutableMapping[str, str]):
    __slots__ = ("_headers", "_normalized")

    def __init__(self, headers: Mapping[str, str] | None = None) -> None:
        if headers is None:
            headers = {}

        self._headers: dict[str, list[str | None]] = {}
        self._normalized: dict[str, str] = {}

        for header_name, header_value in headers.items():
            self.set(header_name, header_value)

    @overload
    def all(self, key: str) -> list[str | None]: ...

    @overload
    def all(self, key: Literal[None] = None) -> dict[str, list[str | None]]: ...

    def all(
        self, key: str | None = None
    ) -> list[str | None] | dict[str, list[str | None]]:
        if key is None:
            return self._headers

        normalized_key = self._normalize_name(key)

        return self._headers.get(normalized_key, []) or []

    @overload
    def get(self, key: str, /) -> str | None: ...

    @overload
    def get(self, key: str, /, default: str | T) -> str | T: ...

    def get(self, key: str, /, default: str | T | None = None) -> str | T | None:
        headers = self.all(key)

        if not headers:
            return default

        return headers[0]

    def set(
        self, name: str, value: str | list[str | None] | None, replace: bool = True
    ) -> None:
        name = self._normalize_name(name)

        if isinstance(value, str) or value is None:
            value = [value]

        if replace or name not in self._headers:
            self._headers[name] = value
        else:
            self._headers[name].extend(value)

    def has(self, name: str) -> bool:
        return self._normalize_name(name) in self._headers

    def remove(self, name: str) -> None:
        name = self._normalize_name(name)

        if name in self._headers:
            del self._headers[name]

    def _normalize_name(self, name: str) -> str:
        if name in self._normalized:
            return self._normalized[name]

        self._normalized[name] = name.lower()

        return self._normalized[name]

    def __getitem__(self, name: str) -> str:
        name = self._normalize_name(name)
        if name not in self._headers:
            raise KeyError(f"Header '{name}' not found.")

        value = self.get(name)

        assert isinstance(value, str)

        return value

    def __setitem__(self, name: str, value: str | list[str | None] | None) -> None:
        self.set(name, value, replace=True)

    def __delitem__(self, name: str) -> None:
        self.remove(name)

    def __iter__(self):
        return iter(self._headers)

    def __len__(self) -> int:
        return len(self._headers)

    def __repr__(self) -> str:
        return f"HeaderBag({self._headers})"

    def encode(self) -> list[tuple[bytes, bytes]]:
        return [
            (
                k.encode("latin-1"),
                ",".join(_ for _ in v if _ is not None).encode("latin-1"),
            )
            for k, v in self._headers.items()
        ]

    def __str__(self) -> str:
        if not self._headers:
            return ""

        headers = sorted(self._headers.items(), key=lambda x: x[0])

        return (
            "\r\n".join(
                f"{k.title()}: {', '.join(_ for _ in v if _ is not None) if v else ''}"
                for k, v in headers
            )
            + "\r\n"
        )
