from typing import Any
from typing import override

from expanse.contracts.cache.synchronous.store import Store


class MemoryStore(Store):
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    @override
    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        self._store[key] = value

        return True

    @override
    def set_many(self, items: dict[str, Any], ttl: int | None = None) -> bool:
        self._store.update(items)

        return True

    @override
    def get(self, key: str) -> Any | None:
        return self._store.get(key)

    @override
    def get_many(self, keys: list[str]) -> dict[str, Any | None]:
        return {key: self._store.get(key) for key in keys}

    @override
    def has(self, key: str) -> bool:
        return key in self._store

    @override
    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]

            return True

        return False

    @override
    def clear(self) -> bool:
        self._store.clear()

        return True
