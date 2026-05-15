from typing import Any
from typing import override

from expanse.cache.synchronous.stores.memory import MemoryStore as SyncMemoryStore
from expanse.contracts.cache.asynchronous.store import Store


class MemoryStore(Store):
    def __init__(self, sync_store: SyncMemoryStore) -> None:
        self._sync_store: SyncMemoryStore = sync_store

    @override
    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return self._sync_store.set(key, value, ttl)

    @override
    async def set_many(self, items: dict[str, Any], ttl: int | None = None) -> bool:
        return self._sync_store.set_many(items, ttl)

    @override
    async def get(self, key: str) -> Any | None:
        return self._sync_store.get(key)

    @override
    async def get_many(self, keys: list[str]) -> dict[str, Any | None]:
        return self._sync_store.get_many(keys)

    @override
    async def has(self, key: str) -> bool:
        return self._sync_store.has(key)

    @override
    async def delete(self, key: str) -> bool:
        return self._sync_store.delete(key)

    @override
    async def clear(self) -> bool:
        return self._sync_store.clear()
