from __future__ import annotations

import asyncio
import time

from typing import TYPE_CHECKING

import pytest

from expanse.cache.synchronous.locks.redis_lock import RedisLock


if TYPE_CHECKING:
    from expanse.redis.synchronous.connections.connection import Connection


pytestmark = pytest.mark.redis


@pytest.fixture()
def lock(connection: Connection) -> RedisLock:
    return RedisLock(connection, "test-lock", ttl=10, owner="owner-1")


def test_acquire_returns_true_when_lock_is_free(lock: RedisLock) -> None:
    assert lock.acquire(blocking=False) is True


def test_acquire_stores_owner_in_redis(lock: RedisLock, connection: Connection) -> None:
    lock.acquire(blocking=False)

    assert connection.get("lock:test-lock") == lock.owner


def test_acquire_returns_false_when_lock_is_held(
    lock: RedisLock, connection: Connection
) -> None:
    other = RedisLock(connection, "test-lock", ttl=10, owner="owner-2")

    lock.acquire(blocking=False)

    assert other.acquire(blocking=False) is False


async def test_acquire_blocks_until_lock_is_released(
    connection: Connection,
) -> None:
    holder = RedisLock(connection, "test-lock", ttl=10, owner="holder")
    waiter = RedisLock(connection, "test-lock", ttl=10, owner="waiter")

    holder.acquire(blocking=False)

    async def release_after_delay() -> None:
        await asyncio.sleep(0.3)
        holder.release()

    asyncio.create_task(release_after_delay())  # noqa: RUF006

    acquired = await asyncio.to_thread(waiter.acquire)

    assert acquired is True
    assert connection.get("lock:test-lock") == "waiter"


def test_acquire_returns_false_on_timeout(connection: Connection) -> None:
    holder = RedisLock(connection, "test-lock", ttl=10, owner="holder")
    waiter = RedisLock(connection, "test-lock", ttl=10, owner="waiter")

    holder.acquire(blocking=False)

    assert waiter.acquire(blocking=True, timeout=0) is False


def test_acquire_sets_ttl_on_key(lock: RedisLock, connection: Connection) -> None:
    lock.acquire(blocking=False)

    ttl = connection.ttl("lock:test-lock")

    assert 0 < ttl <= 10


def test_acquire_without_ttl_sets_no_expiry(connection: Connection) -> None:
    lock = RedisLock(connection, "test-lock", owner="owner-1")

    lock.acquire(blocking=False)

    assert connection.ttl("lock:test-lock") == -1


def test_release_removes_lock(lock: RedisLock, connection: Connection) -> None:
    lock.acquire(blocking=False)

    assert lock.release() is True
    assert connection.get("lock:test-lock") is None


def test_release_returns_false_when_not_owner(
    lock: RedisLock, connection: Connection
) -> None:
    other = RedisLock(connection, "test-lock", ttl=10, owner="owner-2")

    lock.acquire(blocking=False)

    assert other.release() is False
    assert connection.get("lock:test-lock") is not None


def test_release_force_removes_lock_regardless_of_owner(
    lock: RedisLock, connection: Connection
) -> None:
    other = RedisLock(connection, "test-lock", ttl=10, owner="owner-2")

    lock.acquire(blocking=False)

    assert other.release(force=True) is True
    assert connection.get("lock:test-lock") is None


def test_release_returns_false_when_lock_is_not_held(lock: RedisLock) -> None:
    assert lock.release() is False


def test_context_manager_acquires_and_releases(
    lock: RedisLock, connection: Connection
) -> None:
    with lock:
        assert connection.get("lock:test-lock") == lock.owner

    assert connection.get("lock:test-lock") is None


def test_refresh_extends_ttl(lock: RedisLock, connection: Connection) -> None:
    lock.acquire(blocking=False)
    connection.expire("lock:test-lock", 2)

    assert lock.refresh(ttl=30) is True

    ttl = connection.ttl("lock:test-lock")
    assert ttl > 2


def test_refresh_returns_false_when_not_owner(
    lock: RedisLock, connection: Connection
) -> None:
    other = RedisLock(connection, "test-lock", ttl=10, owner="owner-2")

    lock.acquire(blocking=False)

    assert other.refresh(ttl=30) is False


def test_refresh_returns_false_when_lock_not_held(lock: RedisLock) -> None:
    assert lock.refresh(ttl=30) is False


def test_auto_refresh_keeps_lock_alive(connection: Connection) -> None:
    lock = RedisLock(connection, "test-lock", ttl=2, owner="owner-1", refresh=True)

    lock.acquire(blocking=False)
    time.sleep(1.5)

    ttl = connection.ttl("lock:test-lock")
    assert ttl > 1

    lock.release()


def test_get_current_owner_returns_owner_when_held(lock: RedisLock) -> None:
    lock.acquire(blocking=False)

    assert lock.get_current_owner() == lock.owner


def test_get_current_owner_returns_none_when_free(lock: RedisLock) -> None:
    assert lock.get_current_owner() is None


def test_is_owned_by_current_process_returns_true_when_held(lock: RedisLock) -> None:
    lock.acquire(blocking=False)

    assert lock.is_owned_by_current_process() is True


def test_is_owned_by_current_process_returns_false_when_not_held(
    lock: RedisLock,
) -> None:
    assert lock.is_owned_by_current_process() is False
