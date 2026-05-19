from __future__ import annotations

import asyncio

from typing import TYPE_CHECKING

from expanse.cache.asynchronous.locks.memory_lock import MemoryLock
from expanse.cache.asynchronous.stores.memory import MemoryStore
from expanse.cache.synchronous.stores.memory import MemoryStore as SyncMemoryStore


if TYPE_CHECKING:
    from collections.abc import Callable


def make_store() -> MemoryStore:
    return MemoryStore(SyncMemoryStore())


def make_lock_factory(store: MemoryStore) -> Callable[..., MemoryLock]:
    def factory(owner: str = "owner-1", **kwargs: object) -> MemoryLock:
        return MemoryLock(store._sync_store, "test-lock", owner=owner, **kwargs)

    return factory


async def test_acquire_returns_true_when_lock_is_free() -> None:
    store = make_store()
    lock = make_lock_factory(store)()

    assert await lock.acquire(blocking=False) is True


async def test_acquire_returns_false_when_lock_is_held() -> None:
    store = make_store()
    make_lock = make_lock_factory(store)
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    await lock.acquire(blocking=False)

    assert await other.acquire(blocking=False) is False


async def test_acquire_blocks_until_lock_is_released() -> None:
    store = make_store()
    make_lock = make_lock_factory(store)
    holder = make_lock(owner="holder")
    waiter = make_lock(owner="waiter")

    await holder.acquire(blocking=False)

    async def release_after_delay() -> None:
        await asyncio.sleep(0.3)
        await holder.release()

    asyncio.create_task(release_after_delay())  # noqa: RUF006

    assert await waiter.acquire(blocking=True) is True


async def test_acquire_returns_false_on_timeout() -> None:
    store = make_store()
    make_lock = make_lock_factory(store)
    holder = make_lock(owner="holder")
    waiter = make_lock(owner="waiter")

    await holder.acquire(blocking=False)

    assert await waiter.acquire(blocking=True, timeout=0) is False


async def test_release_allows_another_lock_to_acquire() -> None:
    store = make_store()
    make_lock = make_lock_factory(store)
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    await lock.acquire(blocking=False)
    await lock.release()

    assert await other.acquire(blocking=False) is True


async def test_release_force_removes_lock() -> None:
    store = make_store()
    make_lock = make_lock_factory(store)
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    await lock.acquire(blocking=False)
    await other.release(force=True)

    assert await other.acquire(blocking=False) is True


async def test_context_manager_acquires_and_releases() -> None:
    store = make_store()
    make_lock = make_lock_factory(store)
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    async with lock:
        assert await other.acquire(blocking=False) is False

    assert await other.acquire(blocking=False) is True


async def test_get_current_owner_returns_owner() -> None:
    store = make_store()
    lock = make_lock_factory(store)(owner="owner-1")

    await lock.acquire(blocking=False)

    assert await lock.get_current_owner() == "owner-1"


async def test_is_owned_by_current_process_returns_true() -> None:
    store = make_store()
    lock = make_lock_factory(store)()

    await lock.acquire(blocking=False)

    assert await lock.is_owned_by_current_process() is True


async def test_refresh_returns_true() -> None:
    store = make_store()
    lock = make_lock_factory(store)(owner="owner-1", ttl=5)

    await lock.acquire(blocking=False)

    assert await lock.refresh(ttl=10) is True


async def test_refresh_returns_false_when_not_held() -> None:
    store = make_store()
    lock = make_lock_factory(store)(owner="owner-1", ttl=5)

    assert await lock.refresh(ttl=10) is False
