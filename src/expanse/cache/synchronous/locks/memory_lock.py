from __future__ import annotations

import time

from typing import TYPE_CHECKING
from typing import Any
from typing import override

from expanse.cache.synchronous.locks.lock import Lock


if TYPE_CHECKING:
    import threading


class MemoryLock(Lock):
    def __init__(
        self,
        locks: dict[str, dict[str, Any]],
        mutex: threading.Lock,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
    ) -> None:
        super().__init__(name, ttl, owner, refresh=refresh)

        self._locks: dict[str, dict[str, Any]] = locks
        self._mutex: threading.Lock = mutex

    @override
    def _do_acquire(self) -> bool:
        with self._mutex:
            entry = self._locks.get(self._name)
            now = time.time()

            if entry is not None:
                expiration = entry["expiration"]
                if (expiration is None or expiration > now) and entry[
                    "owner"
                ] != self._owner:
                    return False

            self._locks[self._name] = {
                "owner": self._owner,
                "expiration": (now + self._ttl) if self._ttl is not None else None,
            }
            return True

    @override
    def _do_release(self, force: bool = False) -> bool:
        with self._mutex:
            entry = self._locks.get(self._name)
            if entry is None:
                return False

            if force or entry["owner"] == self._owner:
                del self._locks[self._name]
                return True

            return False

    @override
    def get_current_owner(self) -> str | None:
        with self._mutex:
            entry = self._locks.get(self._name)
            if entry is None:
                return None

            expiration = entry["expiration"]
            if expiration is not None and expiration <= time.time():
                return None

            return entry["owner"]

    @override
    def refresh(self, ttl: int | None = None) -> bool:
        ttl = ttl if ttl is not None else self._ttl
        if ttl is None:
            return False

        with self._mutex:
            entry = self._locks.get(self._name)
            if entry is None or entry["owner"] != self._owner:
                return False

            entry["expiration"] = time.time() + ttl
            return True
