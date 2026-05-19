from __future__ import annotations

import threading

from typing import TYPE_CHECKING
from typing import Any
from typing import override

from expanse.contracts.cache.synchronous.store import Store


if TYPE_CHECKING:
    from expanse.contracts.lock.synchronous.lock import Lock


class MemoryStore(Store):
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._locks: dict[str, dict[str, Any]] = {}
        self._mutex: threading.Lock = threading.Lock()

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

    @override
    def lock(
        self,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
    ) -> Lock:
        from expanse.cache.synchronous.locks.memory_lock import MemoryLock

        return MemoryLock(self._locks, self._mutex, name, ttl, owner, refresh)
