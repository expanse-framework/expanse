from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import override

from atomic_lru import CACHE_MISS
from atomic_lru import Cache as LRUCache

from expanse.contracts.cache.cache_item import CacheItem
from expanse.contracts.cache.synchronous.store import Store


if TYPE_CHECKING:
    from expanse.contracts.lock.synchronous.lock import Lock


class MemoryStore(Store):
    def __init__(
        self,
        max_items: int = 1000,
        max_size: int | None = None,
        default_ttl: int | None = None,
    ) -> None:
        self._cache: LRUCache = LRUCache(
            max_items=max_items, size_limit_in_bytes=max_size, default_ttl=default_ttl
        )
        self._locks: dict[str, dict[str, Any]] = {}

    @override
    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        self._cache.set(key, value, ttl=ttl)

        return True

    @override
    def set_many(self, items: dict[str, Any], ttl: int | None = None) -> bool:
        for key, value in items.items():
            self._cache.set(key, value, ttl=ttl)

        return True

    @override
    def get(self, key: str) -> CacheItem:
        result = self._cache.get(key)
        if result is CACHE_MISS:
            return CacheItem(key=key)

        return CacheItem(key=key, value=result, is_hit=True)

    @override
    def get_many(self, keys: list[str]) -> dict[str, CacheItem]:
        results: dict[str, CacheItem] = {}

        for key in keys:
            result = self._cache.get(key)
            results[key] = (
                CacheItem(key=key, value=result, is_hit=True)
                if result is not CACHE_MISS
                else CacheItem(key=key)
            )

        return results

    @override
    def has(self, key: str) -> bool:
        return self.get(key).is_hit

    @override
    def delete(self, key: str) -> bool:
        return self._cache.delete(key)

    @override
    def clear(self) -> bool:
        self._cache.clear()

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

        return MemoryLock(name, ttl, owner, refresh, locks=self._locks)
