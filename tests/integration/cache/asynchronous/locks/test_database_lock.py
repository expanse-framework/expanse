from __future__ import annotations

import asyncio
import time

from typing import TYPE_CHECKING
from typing import Any

import pytest

from expanse.cache.asynchronous.locks.database_lock import DatabaseLock
from expanse.database.asynchronous.database_manager import AsyncDatabaseManager


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from collections.abc import Callable

    from expanse.core.application import Application
    from expanse.testing.command_tester import CommandTester


pytestmark = pytest.mark.db


@pytest.fixture()
async def db(
    app: Application, name: str, command_tester: CommandTester
) -> AsyncDatabaseManager:
    app.config["database"]["default"] = name
    command_tester.command("db migrate").run()
    return await app.container.get(AsyncDatabaseManager)


@pytest.fixture()
async def make_lock(
    db: AsyncDatabaseManager, name: str
) -> AsyncGenerator[Callable[..., DatabaseLock], None]:
    created: list[DatabaseLock] = []

    def factory(
        lock_name: str = "test-lock",
        owner: str = "owner-1",
        ttl: int | None = 10,
        **kwargs: Any,
    ) -> DatabaseLock:
        lock = DatabaseLock(
            connection=db.connection(name),
            table_name="cache_locks",
            name=lock_name,
            owner=owner,
            ttl=ttl,
            **kwargs,
        )
        created.append(lock)
        return lock

    yield factory

    for lock in created:
        if lock._connection.sync_connection:
            await lock._connection.close()


@pytest.fixture()
def lock(make_lock: Callable[..., DatabaseLock]) -> DatabaseLock:
    return make_lock()


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_acquire_returns_true_when_lock_is_free(lock: DatabaseLock) -> None:
    assert await lock.acquire(blocking=False) is True


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_acquire_stores_owner_in_database(
    lock: DatabaseLock, db: AsyncDatabaseManager, name: str
) -> None:
    await lock.acquire(blocking=False)

    async with db.connection(name) as conn:
        row = (
            await conn.execute(
                lock._table.select().where(lock._table.c.key == "test-lock")
            )
        ).first()

    assert row is not None
    assert row[1] == lock.owner


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_acquire_returns_false_when_lock_is_held(
    make_lock: Callable[..., DatabaseLock],
) -> None:
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    await lock.acquire(blocking=False)

    assert await other.acquire(blocking=False) is False


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_acquire_can_reacquire_expired_lock(
    make_lock: Callable[..., DatabaseLock],
) -> None:
    holder = make_lock(owner="owner-1", ttl=1)
    waiter = make_lock(owner="owner-2", ttl=10)

    await holder.acquire(blocking=False)

    await asyncio.sleep(1.1)

    assert await waiter.acquire(blocking=False) is True


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_acquire_blocks_until_lock_is_released(
    make_lock: Callable[..., DatabaseLock],
) -> None:
    holder = make_lock(owner="holder")
    waiter = make_lock(owner="waiter")

    await holder.acquire(blocking=False)

    async def release_after_delay() -> None:
        await asyncio.sleep(0.3)
        await holder.release()

    asyncio.create_task(release_after_delay())  # noqa: RUF006

    assert await waiter.acquire(blocking=True) is True


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_acquire_returns_false_on_timeout(
    make_lock: Callable[..., DatabaseLock],
) -> None:
    holder = make_lock(owner="holder")
    waiter = make_lock(owner="waiter")

    await holder.acquire(blocking=False)

    assert await waiter.acquire(blocking=True, timeout=0) is False


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_acquire_sets_expiration(
    lock: DatabaseLock, db: AsyncDatabaseManager, name: str
) -> None:
    before = int(time.time())
    await lock.acquire(blocking=False)
    after = int(time.time())

    async with db.connection(name) as conn:
        row = (
            await conn.execute(
                lock._table.select().where(lock._table.c.key == "test-lock")
            )
        ).first()

    assert row is not None
    assert before + 10 <= row[2] <= after + 10


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_release_removes_lock(
    lock: DatabaseLock, db: AsyncDatabaseManager, name: str
) -> None:
    await lock.acquire(blocking=False)

    assert await lock.release() is True

    async with db.connection(name) as conn:
        row = (
            await conn.execute(
                lock._table.select().where(lock._table.c.key == "test-lock")
            )
        ).first()

    assert row is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_release_returns_false_when_not_owner(
    make_lock: Callable[..., DatabaseLock], db: AsyncDatabaseManager, name: str
) -> None:
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    await lock.acquire(blocking=False)

    assert await other.release() is False

    async with db.connection(name) as conn:
        row = (
            await conn.execute(
                lock._table.select().where(lock._table.c.key == "test-lock")
            )
        ).first()

    assert row is not None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_release_force_removes_lock_regardless_of_owner(
    make_lock: Callable[..., DatabaseLock], db: AsyncDatabaseManager, name: str
) -> None:
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    await lock.acquire(blocking=False)

    assert await other.release(force=True) is True

    async with db.connection(name) as conn:
        row = (
            await conn.execute(
                lock._table.select().where(lock._table.c.key == "test-lock")
            )
        ).first()

    assert row is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_release_returns_false_when_lock_is_not_held(
    lock: DatabaseLock,
) -> None:
    assert await lock.release() is False


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_context_manager_acquires_and_releases(
    lock: DatabaseLock, db: AsyncDatabaseManager, name: str
) -> None:
    async with lock:
        async with db.connection(name) as conn:
            row = (
                await conn.execute(
                    lock._table.select().where(lock._table.c.key == "test-lock")
                )
            ).first()
        assert row is not None

    async with db.connection(name) as conn:
        row = (
            await conn.execute(
                lock._table.select().where(lock._table.c.key == "test-lock")
            )
        ).first()

    assert row is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_refresh_extends_expiration(
    lock: DatabaseLock, db: AsyncDatabaseManager, name: str
) -> None:
    await lock.acquire(blocking=False)

    async with db.connection(name) as conn:
        row = (
            await conn.execute(
                lock._table.select().where(lock._table.c.key == "test-lock")
            )
        ).first()
    assert row is not None
    original_expiration = row[2]

    assert await lock.refresh(ttl=3600) is True

    async with db.connection(name) as conn:
        row = (
            await conn.execute(
                lock._table.select().where(lock._table.c.key == "test-lock")
            )
        ).first()

    assert row is not None
    assert row[2] > original_expiration


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_refresh_returns_false_when_not_owner(
    make_lock: Callable[..., DatabaseLock],
) -> None:
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    await lock.acquire(blocking=False)

    assert await other.refresh(ttl=3600) is False


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_refresh_returns_false_when_lock_not_held(lock: DatabaseLock) -> None:
    assert await lock.refresh(ttl=3600) is False


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_auto_refresh_keeps_lock_alive(
    make_lock: Callable[..., DatabaseLock], db: AsyncDatabaseManager, name: str
) -> None:
    lock = make_lock(owner="owner-1", ttl=2, refresh=True)

    await lock.acquire(blocking=False)

    async with db.connection(name) as conn:
        row = (
            await conn.execute(
                lock._table.select().where(lock._table.c.key == "test-lock")
            )
        ).first()
    assert row is not None
    original_expiration = row[2]

    await asyncio.sleep(1.5)

    async with db.connection(name) as conn:
        row = (
            await conn.execute(
                lock._table.select().where(lock._table.c.key == "test-lock")
            )
        ).first()

    assert row is not None
    assert row[2] >= original_expiration

    await lock.release()


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_get_current_owner_returns_owner_when_held(lock: DatabaseLock) -> None:
    await lock.acquire(blocking=False)

    assert await lock.get_current_owner() == lock.owner


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_get_current_owner_returns_none_when_free(lock: DatabaseLock) -> None:
    assert await lock.get_current_owner() is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_is_owned_by_current_process_returns_true_when_held(
    lock: DatabaseLock,
) -> None:
    await lock.acquire(blocking=False)

    assert await lock.is_owned_by_current_process() is True


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_is_owned_by_current_process_returns_false_when_not_held(
    lock: DatabaseLock,
) -> None:
    assert await lock.is_owned_by_current_process() is False
