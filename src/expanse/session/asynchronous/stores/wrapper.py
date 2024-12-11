from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.session.asynchronous.stores.store import AsyncStore
from expanse.support._concurrency import run_in_threadpool


if TYPE_CHECKING:
    from expanse.http.request import Request
    from expanse.session.synchronous.stores.store import Store as SyncStore


class AsyncWrapperStore(AsyncStore):
    def __init__(self, store: SyncStore) -> None:
        self._store = store

    async def read(self, id: str) -> str:
        return await run_in_threadpool(self._store.read, id)

    async def write(self, id: str, data: str, request: Request | None = None) -> None:
        await run_in_threadpool(self._store.write, id, data, request)

    async def delete(self, id: str) -> None:
        await run_in_threadpool(self._store.delete, id)

    async def clear(self) -> int:
        return await run_in_threadpool(self._store.clear)
