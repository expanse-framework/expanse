from __future__ import annotations

from collections.abc import Iterator
from collections.abc import MutableMapping
from typing import Any
from typing import override


class Context(MutableMapping[str, Any]):
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    @override
    def __contains__(self, key: object) -> bool:
        return key in self._data

    @override
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    @override
    def pop(self, key: str, *args: Any) -> Any:
        return self._data.pop(key, *args)

    @override
    def popitem(self) -> tuple[str, Any]:
        return self._data.popitem()

    @override
    def clear(self) -> None:
        self._data.clear()

    @override
    def update(self, other: Any = (), /, **kwargs: Any) -> None:
        self._data.update(other, **kwargs)

    @override
    def setdefault(self, key: str, default: Any = None) -> Any:
        return self._data.setdefault(key, default)
