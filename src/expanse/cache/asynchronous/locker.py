from typing import override

from expanse.contracts.cache.asynchronous.locker import Locker as LockerContract
from expanse.contracts.cache.asynchronous.store import Store
from expanse.contracts.lock.asynchronous.lock import Lock


class Locker(LockerContract):
    def __init__(self, store: Store) -> None:
        self._store: Store = store

    @override
    def lock(self, name: str, ttl: int | None = None) -> Lock:
        return self._store.lock(name, ttl, refresh=True)
