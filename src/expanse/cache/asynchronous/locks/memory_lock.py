from __future__ import annotations

from typing import TYPE_CHECKING
from typing import override

from expanse.cache.asynchronous.locks.lock import Lock
from expanse.cache.synchronous.locks.memory_lock import MemoryLock as SyncMemoryLock


if TYPE_CHECKING:
    from expanse.cache.synchronous.stores.memory import MemoryStore as SyncMemoryStore


class MemoryLock(Lock):
    def __init__(
        self,
        sync_store: SyncMemoryStore,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
    ) -> None:
        super().__init__(name, ttl, owner, refresh=refresh)

        self._sync_lock: SyncMemoryLock = SyncMemoryLock(
            name, ttl, self._owner, refresh=False, locks=sync_store._locks
        )

    @override
    async def _do_acquire(self) -> bool:
        return self._sync_lock._do_acquire()

    @override
    async def _do_release(self, force: bool = False) -> bool:
        return self._sync_lock._do_release(force)

    @override
    async def get_current_owner(self) -> str | None:
        return self._sync_lock.get_current_owner()

    @override
    async def refresh(self, ttl: int | None = None) -> bool:
        return self._sync_lock.refresh(ttl)
