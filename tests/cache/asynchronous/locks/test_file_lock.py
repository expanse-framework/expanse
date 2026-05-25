from __future__ import annotations

import asyncio

from typing import TYPE_CHECKING
from typing import Any

import pytest

from expanse.cache.asynchronous.locks.file_lock import FileLock


if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@pytest.fixture()
def lock_path(tmp_path: Path) -> Path:
    return tmp_path / "test.lock"


@pytest.fixture()
def make_lock(lock_path: Path) -> Callable[..., FileLock]:
    def factory(owner: str = "owner-1", **kwargs: Any) -> FileLock:
        return FileLock(lock_path, "test-lock", owner=owner, **kwargs)

    return factory


@pytest.fixture()
def lock(make_lock: Callable[..., FileLock]) -> FileLock:
    return make_lock()


async def test_acquire_returns_true_when_lock_is_free(lock: FileLock) -> None:
    assert await lock.acquire(blocking=False) is True


async def test_acquire_returns_false_when_lock_is_held(
    make_lock: Callable[..., FileLock],
) -> None:
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    await lock.acquire(blocking=False)

    assert await other.acquire(blocking=False) is False


async def test_acquire_blocks_until_lock_is_released(
    make_lock: Callable[..., FileLock],
) -> None:
    holder = make_lock(owner="holder")
    waiter = make_lock(owner="waiter")

    await holder.acquire(blocking=False)

    async def release_after_delay() -> None:
        await asyncio.sleep(0.3)
        await holder.release()

    asyncio.create_task(release_after_delay())  # noqa: RUF006

    assert await waiter.acquire(blocking=True) is True


async def test_acquire_returns_false_on_timeout(
    make_lock: Callable[..., FileLock],
) -> None:
    holder = make_lock(owner="holder")
    waiter = make_lock(owner="waiter")

    await holder.acquire(blocking=False)

    assert await waiter.acquire(blocking=True, timeout=0) is False


async def test_release_allows_another_lock_to_acquire(
    make_lock: Callable[..., FileLock],
) -> None:
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    await lock.acquire(blocking=False)
    await lock.release()

    assert await other.acquire(blocking=False) is True


async def test_context_manager_acquires_and_releases(
    make_lock: Callable[..., FileLock], lock_path: Path
) -> None:
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    async with lock:
        assert lock_path.exists()
        assert await other.acquire(blocking=False) is False

    assert await other.acquire(blocking=False) is True


async def test_get_current_owner_returns_none(lock: FileLock) -> None:
    await lock.acquire(blocking=False)

    assert await lock.get_current_owner() is None


async def test_is_owned_by_current_process_returns_true(lock: FileLock) -> None:
    await lock.acquire(blocking=False)

    assert await lock.is_owned_by_current_process() is True


async def test_refresh_returns_true(lock: FileLock) -> None:
    await lock.acquire(blocking=False)

    assert await lock.refresh() is True
