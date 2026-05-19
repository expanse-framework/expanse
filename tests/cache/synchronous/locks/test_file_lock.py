from __future__ import annotations

import asyncio

from typing import TYPE_CHECKING

import pytest

from expanse.cache.synchronous.locks.file_lock import FileLock


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator
    from pathlib import Path


@pytest.fixture()
def lock_path(tmp_path: Path) -> Path:
    return tmp_path / "test.lock"


@pytest.fixture()
def make_lock(lock_path: Path) -> Generator[Callable[..., FileLock], None, None]:
    created: list[FileLock] = []

    def factory(owner: str = "owner-1", **kwargs: object) -> FileLock:
        lock = FileLock(lock_path, "test-lock", owner=owner, **kwargs)
        created.append(lock)
        return lock

    yield factory

    for lock in created:
        lock.release(force=True)


@pytest.fixture()
def lock(make_lock: Callable[..., FileLock]) -> FileLock:
    return make_lock()


def test_acquire_returns_true_when_lock_is_free(lock: FileLock) -> None:
    assert lock.acquire(blocking=False) is True


def test_acquire_returns_false_when_lock_is_held(
    make_lock: Callable[..., FileLock],
) -> None:
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    lock.acquire(blocking=False)

    assert other.acquire(blocking=False) is False


async def test_acquire_blocks_until_lock_is_released(
    make_lock: Callable[..., FileLock],
) -> None:
    holder = make_lock(owner="holder")
    waiter = make_lock(owner="waiter")

    holder.acquire(blocking=False)

    async def release_after_delay() -> None:
        await asyncio.sleep(0.3)
        holder.release()

    asyncio.create_task(release_after_delay())  # noqa: RUF006

    acquired = await asyncio.to_thread(waiter.acquire)

    assert acquired is True


def test_acquire_returns_false_on_timeout(
    make_lock: Callable[..., FileLock],
) -> None:
    holder = make_lock(owner="holder")
    waiter = make_lock(owner="waiter")

    holder.acquire(blocking=False)

    assert waiter.acquire(blocking=True, timeout=0) is False


def test_release_allows_another_lock_to_acquire(
    make_lock: Callable[..., FileLock],
) -> None:
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    lock.acquire(blocking=False)
    lock.release()

    assert other.acquire(blocking=False) is True


def test_context_manager_acquires_and_releases(
    make_lock: Callable[..., FileLock], lock_path: Path
) -> None:
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    with lock:
        assert lock_path.exists()
        assert other.acquire(blocking=False) is False

    assert other.acquire(blocking=False) is True


def test_get_current_owner_returns_none(lock: FileLock) -> None:
    lock.acquire(blocking=False)

    assert lock.get_current_owner() is None


def test_is_owned_by_current_process_returns_true(lock: FileLock) -> None:
    lock.acquire(blocking=False)

    assert lock.is_owned_by_current_process() is True


def test_refresh_returns_true(lock: FileLock) -> None:
    lock.acquire(blocking=False)

    assert lock.refresh() is True
