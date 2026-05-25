from __future__ import annotations

import asyncio

from typing import TYPE_CHECKING

import pytest

from expanse.cache.asynchronous.locks.redis_lock import RedisLock


if TYPE_CHECKING:
    from expanse.redis.asynchronous.connections.connection import Connection


pytestmark = pytest.mark.redis


@pytest.fixture()
def lock(connection: Connection) -> RedisLock:
    return RedisLock(connection, "test-lock", ttl=10, owner="owner-1")


async def test_acquire_returns_true_when_lock_is_free(lock: RedisLock) -> None:
    assert await lock.acquire(blocking=False) is True


async def test_acquire_stores_owner_in_redis(
    lock: RedisLock, connection: Connection
) -> None:
    await lock.acquire(blocking=False)

    assert await connection.get("lock:test-lock") == lock.owner


async def test_acquire_returns_false_when_lock_is_held(
    lock: RedisLock, connection: Connection
) -> None:
    other = RedisLock(connection, "test-lock", ttl=10, owner="owner-2")

    await lock.acquire(blocking=False)

    assert await other.acquire(blocking=False) is False


async def test_acquire_blocks_until_lock_is_released(
    connection: Connection,
) -> None:
    holder = RedisLock(connection, "test-lock", ttl=10, owner="holder")
    waiter = RedisLock(connection, "test-lock", ttl=10, owner="waiter")

    await holder.acquire(blocking=False)

    async def release_after_delay() -> None:
        await asyncio.sleep(0.3)
        await holder.release()

    asyncio.create_task(release_after_delay())  # noqa: RUF006

    assert await waiter.acquire(blocking=True) is True
    assert await connection.get("lock:test-lock") == "waiter"


async def test_acquire_returns_false_on_timeout(connection: Connection) -> None:
    holder = RedisLock(connection, "test-lock", ttl=10, owner="holder")
    waiter = RedisLock(connection, "test-lock", ttl=10, owner="waiter")

    await holder.acquire(blocking=False)

    assert await waiter.acquire(blocking=True, timeout=0) is False


async def test_acquire_sets_ttl_on_key(lock: RedisLock, connection: Connection) -> None:
    await lock.acquire(blocking=False)

    ttl = await connection.ttl("lock:test-lock")

    assert 0 < ttl <= 10


async def test_acquire_without_ttl_sets_no_expiry(connection: Connection) -> None:
    lock = RedisLock(connection, "test-lock", owner="owner-1")

    await lock.acquire(blocking=False)

    assert await connection.ttl("lock:test-lock") == -1


async def test_release_removes_lock(lock: RedisLock, connection: Connection) -> None:
    await lock.acquire(blocking=False)

    assert await lock.release() is True
    assert await connection.get("lock:test-lock") is None


async def test_release_returns_false_when_not_owner(
    lock: RedisLock, connection: Connection
) -> None:
    other = RedisLock(connection, "test-lock", ttl=10, owner="owner-2")

    await lock.acquire(blocking=False)

    assert await other.release() is False
    assert await connection.get("lock:test-lock") is not None


async def test_release_force_removes_lock_regardless_of_owner(
    lock: RedisLock, connection: Connection
) -> None:
    other = RedisLock(connection, "test-lock", ttl=10, owner="owner-2")

    await lock.acquire(blocking=False)

    assert await other.release(force=True) is True
    assert await connection.get("lock:test-lock") is None


async def test_release_returns_false_when_lock_is_not_held(
    lock: RedisLock,
) -> None:
    assert await lock.release() is False


async def test_context_manager_acquires_and_releases(
    lock: RedisLock, connection: Connection
) -> None:
    async with lock:
        assert await connection.get("lock:test-lock") == lock.owner

    assert await connection.get("lock:test-lock") is None


async def test_refresh_extends_ttl(lock: RedisLock, connection: Connection) -> None:
    await lock.acquire(blocking=False)
    await connection.expire("lock:test-lock", 2)

    assert await lock.refresh(ttl=30) is True

    ttl = await connection.ttl("lock:test-lock")
    assert ttl > 2


async def test_refresh_returns_false_when_not_owner(
    lock: RedisLock, connection: Connection
) -> None:
    other = RedisLock(connection, "test-lock", ttl=10, owner="owner-2")

    await lock.acquire(blocking=False)

    assert await other.refresh(ttl=30) is False


async def test_refresh_returns_false_when_lock_not_held(lock: RedisLock) -> None:
    assert await lock.refresh(ttl=30) is False


async def test_auto_refresh_keeps_lock_alive(connection: Connection) -> None:
    lock = RedisLock(connection, "test-lock", ttl=2, owner="owner-1", refresh=True)

    await lock.acquire(blocking=False)
    await asyncio.sleep(1.5)

    ttl = await connection.ttl("lock:test-lock")
    assert ttl > 1

    await lock.release()


async def test_get_current_owner_returns_owner_when_held(
    lock: RedisLock,
) -> None:
    await lock.acquire(blocking=False)

    assert await lock.get_current_owner() == lock.owner


async def test_get_current_owner_returns_none_when_free(lock: RedisLock) -> None:
    assert await lock.get_current_owner() is None


async def test_is_owned_by_current_process_returns_true_when_held(
    lock: RedisLock,
) -> None:
    await lock.acquire(blocking=False)

    assert await lock.is_owned_by_current_process() is True


async def test_is_owned_by_current_process_returns_false_when_not_held(
    lock: RedisLock,
) -> None:
    assert await lock.is_owned_by_current_process() is False
