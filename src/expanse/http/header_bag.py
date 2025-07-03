from collections.abc import Mapping
from collections.abc import MutableMapping
from collections.abc import dict_items
from typing import Literal
from typing import overload


class HeaderBag(MutableMapping[str, str]):
    __slots__ = ("_headers",)

    def __init__(self, headers: MutableMapping[str, str] | None = None) -> None:
        self._headers: dict[str, list[str | None]] = {}

        for header_name, header_value in headers.items():
            self.set(header_name, header_value)

    @overload
    def all(self, key: str) -> list[str | None]: ...

    @overload
    def all(self, key: Literal[None] = None) -> dict[str, list[str]]: ...

    def all(self, key: str | None = None) -> dict[str, list[str]]:
        if key is None:
            return self._headers

        normalized_key = self._normalize_name(key)

        return {normalized_key: self._headers.get(normalized_key, [])}

    def get(self, key: str, default: str | None = None) -> str | None:
        headers = self.all(key)

        normalized_key = self._normalize_name(key)

        if normalized_key not in headers:
            return default

        if headers[0] is None:
            return None

        return headers[0]

    def set(
        self, name: str, value: str | list[str] | None, replace: bool = True
    ) -> None:
        name = self._normalize_name(name)

        if isinstance(value, str):
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
        return name.lower().replace("_", "-")

    def __getitem__(self, name: str) -> str | None:
        name = self._normalize_name(name)
        if name not in self._headers:
            raise KeyError(f"Header '{name}' not found.")

        return self.get(name)

    def __setitem__(self, name: str, value: str | list[str] | None) -> None:
        self.set(name, value, replace=True)

    def __delitem__(self, name: str) -> None:
        self.remove(name)

    def __iter__(self):
        return iter(self._headers)

    def __len__(self) -> int:
        return len(self._headers)

    def __repr__(self) -> str:
        return f"HeaderBag({self._headers})"

    def __contains__(self, name: str) -> bool:
        return self.has(name)

    def clear(self) -> None:
        self._headers.clear()

    def pop(self, name: str, default: str | None = None) -> str | None:
        return self._headers.pop(name, default)

    def setdefault(self, key, default=None, /) -> None:
        key = self._normalize_name(key)

        self._headers.setdefault(key, default)

    def update(self, other: Mapping[str, str], **kwargs) -> None:
        for key, value in {**other, **kwargs}.items():
            self.set(key, value, replace=True)

    def items(self) -> dict_items[str, list[str]]:
        return self._headers.items()

    def encode(self) -> list[tuple[bytes, bytes]]:
        return [
            (k.encode("latin-1"), ",".join(v).encode("latin-1"))
            for k, v in self._headers.items()
        ]
