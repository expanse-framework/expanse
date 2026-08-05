from __future__ import annotations

from collections.abc import Iterator
from collections.abc import MutableMapping
from typing import Any
from typing import cast
from typing import overload
from typing import override


_NOT_FOUND = object()

type _NestedValue[T] = T | dict[str, _NestedValue[T]]


class DeepMutableMapping[T](MutableMapping[str, T]):
    def __init__(self, **data: _NestedValue[T]) -> None:
        self._data: dict[str, _NestedValue[T]] = data

    def __getitem__(self, key: str) -> T:
        data: Any = self._data

        parts = key.split(".")
        for part in parts:
            if not isinstance(data, dict) or part not in data:
                raise KeyError(key)

            data = data[part]

        return data

    def __setitem__(self, key: str, value: T) -> None:
        data: dict[str, Any] = self._data

        parts = key.split(".")
        count = len(parts)
        for i, part in enumerate(parts):
            if i == count - 1:
                data[part] = value
                return

            if part not in data:
                data[part] = {}
            elif not isinstance(data[part], dict):
                raise TypeError(f"Cannot set {key!r}: {part!r} is not a mapping")

            data = data[part]

    def __delitem__(self, key: str) -> None:
        data: dict[str, Any] = self._data

        parts = key.split(".")
        count = len(parts)
        for i, part in enumerate(parts):
            if not isinstance(data, dict) or part not in data:
                raise KeyError(key)

            if i == count - 1:
                del data[part]
                return

            data = data[part]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    @override
    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False

        data: Any = self._data

        parts = key.split(".")
        for part in parts:
            if not isinstance(data, dict) or part not in data:
                return False

            data = data[part]

        return True

    @overload
    def get(self, key: str) -> T | None: ...
    @overload
    def get(self, key: str, default: T) -> T: ...
    @overload
    def get[D](self, key: str, default: D) -> T | D: ...
    @override
    def get(self, key: str, default: Any = None) -> Any:
        data: Any = self._data

        parts = key.split(".")
        for part in parts:
            if not isinstance(data, dict) or part not in data:
                return default

            data = data[part]

        return data

    @overload
    def pop(self, key: str) -> T: ...
    @overload
    def pop(self, key: str, default: T) -> T: ...
    @overload
    def pop[D](self, key: str, default: D) -> T | D: ...
    @override
    def pop(self, key: str, default: Any = _NOT_FOUND) -> Any:
        data: Any = self._data

        parts = key.split(".")
        count = len(parts)
        for i, part in enumerate(parts):
            if not isinstance(data, dict) or part not in data:
                if default is _NOT_FOUND:
                    raise KeyError(key)
                return default

            if i == count - 1:
                if default is _NOT_FOUND:
                    return data.pop(part)
                return data.pop(part, default)

            data = data[part]

        raise KeyError(key)

    @override
    def popitem(self) -> tuple[str, T]:
        key, value = self._data.popitem()

        return key, cast("T", value)

    @override
    def clear(self) -> None:
        self._data.clear()

    @override
    def update(self, other: Any = (), /, **kwargs: Any) -> None:
        self._data.update(other, **kwargs)

    @override
    def setdefault(self, key: str, default: Any = None) -> Any:
        return self._data.setdefault(key, default)
