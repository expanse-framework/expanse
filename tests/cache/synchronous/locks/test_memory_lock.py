from __future__ import annotations

import threading
import time

from typing import TYPE_CHECKING

from expanse.cache.synchronous.locks.memory_lock import MemoryLock
from expanse.cache.synchronous.stores.memory import MemoryStore


if TYPE_CHECKING:
    from collections.abc import Callable


def make_store() -> MemoryStore:
    return MemoryStore()


def make_lock_factory(store: MemoryStore) -> Callable[..., MemoryLock]:
    def factory(owner: str = "owner-1", **kwargs: object) -> MemoryLock:
        return MemoryLock(
            store._locks, store._mutex, "test-lock", owner=owner, **kwargs
        )

    return factory


def test_acquire_returns_true_when_lock_is_free() -> None:
    store = make_store()
    lock = make_lock_factory(store)()

    assert lock.acquire(blocking=False) is True


def test_acquire_returns_false_when_lock_is_held() -> None:
    store = make_store()
    make_lock = make_lock_factory(store)
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    lock.acquire(blocking=False)

    assert other.acquire(blocking=False) is False


def test_acquire_blocks_until_lock_is_released() -> None:
    store = make_store()
    make_lock = make_lock_factory(store)
    holder = make_lock(owner="holder")
    waiter = make_lock(owner="waiter")

    holder.acquire(blocking=False)

    def release_after_delay() -> None:
        time.sleep(0.3)
        holder.release()

    threading.Thread(target=release_after_delay, daemon=True).start()

    assert waiter.acquire(blocking=True) is True


def test_acquire_returns_false_on_timeout() -> None:
    store = make_store()
    make_lock = make_lock_factory(store)
    holder = make_lock(owner="holder")
    waiter = make_lock(owner="waiter")

    holder.acquire(blocking=False)

    assert waiter.acquire(blocking=True, timeout=0) is False


def test_acquire_takes_expired_lock() -> None:
    store = make_store()
    make_lock = make_lock_factory(store)
    holder = make_lock(owner="holder", ttl=1)
    waiter = make_lock(owner="waiter")

    holder.acquire(blocking=False)

    time.sleep(1.1)

    assert waiter.acquire(blocking=False) is True


def test_release_allows_another_lock_to_acquire() -> None:
    store = make_store()
    make_lock = make_lock_factory(store)
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    lock.acquire(blocking=False)
    lock.release()

    assert other.acquire(blocking=False) is True


def test_release_force_removes_lock() -> None:
    store = make_store()
    make_lock = make_lock_factory(store)
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    lock.acquire(blocking=False)
    other.release(force=True)

    assert other.acquire(blocking=False) is True


def test_context_manager_acquires_and_releases() -> None:
    store = make_store()
    make_lock = make_lock_factory(store)
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    with lock:
        assert other.acquire(blocking=False) is False

    assert other.acquire(blocking=False) is True


def test_get_current_owner_returns_owner() -> None:
    store = make_store()
    lock = make_lock_factory(store)(owner="owner-1")

    lock.acquire(blocking=False)

    assert lock.get_current_owner() == "owner-1"


def test_get_current_owner_returns_none_when_expired() -> None:
    store = make_store()
    lock = make_lock_factory(store)(owner="owner-1", ttl=1)

    lock.acquire(blocking=False)
    time.sleep(1.1)

    assert lock.get_current_owner() is None


def test_is_owned_by_current_process_returns_true() -> None:
    store = make_store()
    lock = make_lock_factory(store)()

    lock.acquire(blocking=False)

    assert lock.is_owned_by_current_process() is True


def test_refresh_extends_expiration() -> None:
    store = make_store()
    make_lock = make_lock_factory(store)
    lock = make_lock(owner="owner-1", ttl=1)
    other = make_lock(owner="owner-2")

    lock.acquire(blocking=False)
    lock.refresh(ttl=10)

    time.sleep(1.1)

    assert other.acquire(blocking=False) is False


def test_refresh_returns_false_when_not_held() -> None:
    store = make_store()
    lock = make_lock_factory(store)(owner="owner-1", ttl=5)

    assert lock.refresh(ttl=10) is False
