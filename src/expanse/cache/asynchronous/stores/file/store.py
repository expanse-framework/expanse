from typing import Any
from typing import override

from expanse.cache.synchronous.stores.file.store import FileStore as SyncFileStore
from expanse.contracts.cache.asynchronous.store import Store
from expanse.support._concurrency import run_in_threadpool


class FileStore(Store):
    def __init__(self, sync_store: SyncFileStore) -> None:
        self._sync_store: SyncFileStore = sync_store

    @override
    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return await run_in_threadpool(self._sync_store.set, key, value, ttl)

    @override
    async def set_many(self, items: dict[str, Any], ttl: int | None = None) -> bool:
        return await run_in_threadpool(self._sync_store.set_many, items, ttl)

    @override
    async def get(self, key: str) -> Any | None:
        return await run_in_threadpool(self._sync_store.get, key)

    @override
    async def get_many(self, keys: list[str]) -> dict[str, Any | None]:
        return await run_in_threadpool(self._sync_store.get_many, keys)

    @override
    async def has(self, key: str) -> bool:
        return await run_in_threadpool(self._sync_store.has, key)

    @override
    async def delete(self, key: str) -> bool:
        return await run_in_threadpool(self._sync_store.delete, key)

    @override
    async def clear(self) -> bool:
        return await run_in_threadpool(self._sync_store.clear)
