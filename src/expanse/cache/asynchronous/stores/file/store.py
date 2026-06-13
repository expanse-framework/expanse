from typing import TYPE_CHECKING
from typing import Any
from typing import override

from expanse.cache.synchronous.stores.file.store import FileStore as SyncFileStore
from expanse.contracts.cache.asynchronous.store import Store
from expanse.contracts.cache.cache_item import CacheItem
from expanse.support._concurrency import sync_to_async


if TYPE_CHECKING:
    from expanse.contracts.lock.asynchronous.lock import Lock


class FileStore(Store):
    def __init__(self, sync_store: SyncFileStore) -> None:
        self._sync_store: SyncFileStore = sync_store

    @override
    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return await sync_to_async(self._sync_store.set, key, value, ttl)

    @override
    async def set_many(self, items: dict[str, Any], ttl: int | None = None) -> bool:
        return await sync_to_async(self._sync_store.set_many, items, ttl)

    @override
    async def get(self, key: str) -> CacheItem:
        return await sync_to_async(self._sync_store.get, key)

    @override
    async def get_many(self, keys: list[str]) -> dict[str, CacheItem]:
        return await sync_to_async(self._sync_store.get_many, keys)

    @override
    async def has(self, key: str) -> bool:
        return await sync_to_async(self._sync_store.has, key)

    @override
    async def delete(self, key: str) -> bool:
        return await sync_to_async(self._sync_store.delete, key)

    @override
    async def clear(self) -> bool:
        return await sync_to_async(self._sync_store.clear)

    @override
    def lock(
        self,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
    ) -> "Lock":
        from expanse.cache.asynchronous.locks.file_lock import FileLock

        lock_name = f"lock:{name}"
        if self._sync_store._locks_path is not None:
            lock_path = self._sync_store._locks_path.joinpath(
                self._sync_store._path_for_key(name).relative_to(self._sync_store._path)
            )
        else:
            lock_path = self._sync_store._path.joinpath(
                self._sync_store._path_for_key(lock_name).relative_to(
                    self._sync_store._path
                )
            )

        return FileLock(lock_path, name, ttl, owner, refresh=refresh)
