import os

from pathlib import Path
from typing import override

from filelock import BaseFileLock as _BaseFileLock
from filelock import FileLock as _FileLock

from expanse.cache.synchronous.locks.lock import Lock


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

        self._lock: _BaseFileLock = _FileLock(path)

    @override
    def _do_acquire(self) -> bool:
        try:
            self._lock.acquire(blocking=False)

            return True
        except BaseException:
            return False

    @override
    def _do_release(self, force: bool = False) -> bool:
        if force:
            try:
                os.remove(self._lock.lock_file)
            except Exception:
                return False

            return True

        try:
            self._lock.release(True)
        except Exception:
            return False

        return True

    @override
    def get_current_owner(self) -> str | None:
        return None

    @override
    def is_owned_by_current_process(self) -> bool:
        # Always return True here since we don't have a way to determine the owner of the lock when using file locks.
        return True

    @override
    def refresh(self, ttl: int | None = None) -> bool:
        return True
