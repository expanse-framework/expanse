from collections.abc import Iterator
from collections.abc import MutableMapping
from typing import Any
from typing import override


class Context(MutableMapping[str, Any]):
    def __init__(self) -> None:
        self._data: dict[str, object] = {}

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
    def clear(self) -> None:
        return self._data.clear()
