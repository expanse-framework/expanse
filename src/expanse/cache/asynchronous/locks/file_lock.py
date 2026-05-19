from pathlib import Path
from typing import override

from expanse.cache.asynchronous.locks.lock import Lock
from expanse.cache.synchronous.locks.file_lock import FileLock as SyncFileLock
from expanse.support._concurrency import run_in_threadpool


class FileLock(Lock):
    def __init__(
        self,
        path: Path,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
    ) -> None:
        super().__init__(name, ttl, owner, refresh=False)

        self._sync_lock: SyncFileLock = SyncFileLock(
            path, name, ttl, self._owner, refresh=False
        )

    @override
    async def _do_acquire(self) -> bool:
        return await run_in_threadpool(self._sync_lock._do_acquire)

    @override
    async def _do_release(self, force: bool = False) -> bool:
        return await run_in_threadpool(self._sync_lock._do_release, force)

    @override
    async def refresh(self, ttl: int | None = None) -> bool:
        return True

    @override
    async def get_current_owner(self) -> str | None:
        return None

    @override
    async def is_owned_by_current_process(self) -> bool:
        return True
