from __future__ import annotations

import asyncio
import time

from typing import TYPE_CHECKING

import pytest

from expanse.cache.synchronous.locks.database_lock import DatabaseLock
from expanse.database.synchronous.database_manager import DatabaseManager


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator

    from expanse.core.application import Application
    from expanse.testing.command_tester import CommandTester


pytestmark = pytest.mark.db


@pytest.fixture()
async def db(
    app: Application, name: str, command_tester: CommandTester
) -> DatabaseManager:
    app.config["database"]["default"] = name
    command_tester.command("db migrate").run()
    return await app.container.get(DatabaseManager)


@pytest.fixture()
def make_lock(
    db: DatabaseManager, name: str
) -> Generator[Callable[..., DatabaseLock], None, None]:
    created: list[DatabaseLock] = []

    def factory(
        lock_name: str = "test-lock",
        owner: str = "owner-1",
        ttl: int | None = 10,
        **kwargs: object,
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
        if not lock._connection.closed:
            lock._connection.close()


@pytest.fixture()
def lock(make_lock: Callable[..., DatabaseLock]) -> DatabaseLock:
    return make_lock()


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_acquire_returns_true_when_lock_is_free(lock: DatabaseLock) -> None:
    assert lock.acquire(blocking=False) is True


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_acquire_stores_owner_in_database(
    lock: DatabaseLock, db: DatabaseManager, name: str
) -> None:
    lock.acquire(blocking=False)

    with db.connection(name) as conn:
        row = conn.execute(
            lock._table.select().where(lock._table.c.key == "test-lock")
        ).first()

    assert row is not None
    assert row[1] == lock.owner


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_acquire_returns_false_when_lock_is_held(
    make_lock: Callable[..., DatabaseLock],
) -> None:
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    lock.acquire(blocking=False)

    assert other.acquire(blocking=False) is False


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_acquire_can_reacquire_expired_lock(
    make_lock: Callable[..., DatabaseLock],
) -> None:
    holder = make_lock(owner="owner-1", ttl=1)
    waiter = make_lock(owner="owner-2", ttl=10)

    holder.acquire(blocking=False)

    time.sleep(1.1)

    assert waiter.acquire(blocking=False) is True


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_acquire_blocks_until_lock_is_released(
    make_lock: Callable[..., DatabaseLock],
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


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_acquire_returns_false_on_timeout(
    make_lock: Callable[..., DatabaseLock],
) -> None:
    holder = make_lock(owner="holder")
    waiter = make_lock(owner="waiter")

    holder.acquire(blocking=False)

    assert waiter.acquire(blocking=True, timeout=0) is False


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_acquire_sets_expiration(
    lock: DatabaseLock, db: DatabaseManager, name: str
) -> None:
    before = int(time.time())
    lock.acquire(blocking=False)
    after = int(time.time())

    with db.connection(name) as conn:
        row = conn.execute(
            lock._table.select().where(lock._table.c.key == "test-lock")
        ).first()

    assert row is not None
    assert before + 10 <= row[2] <= after + 10


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_release_removes_lock(
    lock: DatabaseLock, db: DatabaseManager, name: str
) -> None:
    lock.acquire(blocking=False)

    assert lock.release() is True

    with db.connection(name) as conn:
        row = conn.execute(
            lock._table.select().where(lock._table.c.key == "test-lock")
        ).first()

    assert row is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_release_returns_false_when_not_owner(
    make_lock: Callable[..., DatabaseLock], db: DatabaseManager, name: str
) -> None:
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    lock.acquire(blocking=False)

    assert other.release() is False

    with db.connection(name) as conn:
        row = conn.execute(
            lock._table.select().where(lock._table.c.key == "test-lock")
        ).first()

    assert row is not None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_release_force_removes_lock_regardless_of_owner(
    make_lock: Callable[..., DatabaseLock], db: DatabaseManager, name: str
) -> None:
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    lock.acquire(blocking=False)

    assert other.release(force=True) is True

    with db.connection(name) as conn:
        row = conn.execute(
            lock._table.select().where(lock._table.c.key == "test-lock")
        ).first()

    assert row is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_release_returns_false_when_lock_is_not_held(lock: DatabaseLock) -> None:
    assert lock.release() is False


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_context_manager_acquires_and_releases(
    lock: DatabaseLock, db: DatabaseManager, name: str
) -> None:
    with lock:
        with db.connection(name) as conn:
            row = conn.execute(
                lock._table.select().where(lock._table.c.key == "test-lock")
            ).first()
        assert row is not None

    with db.connection(name) as conn:
        row = conn.execute(
            lock._table.select().where(lock._table.c.key == "test-lock")
        ).first()

    assert row is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_refresh_extends_expiration(
    lock: DatabaseLock, db: DatabaseManager, name: str
) -> None:
    lock.acquire(blocking=False)

    with db.connection(name) as conn:
        row = conn.execute(
            lock._table.select().where(lock._table.c.key == "test-lock")
        ).first()
    original_expiration = row[2]

    assert lock.refresh(ttl=3600) is True

    with db.connection(name) as conn:
        row = conn.execute(
            lock._table.select().where(lock._table.c.key == "test-lock")
        ).first()

    assert row[2] > original_expiration


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_refresh_returns_false_when_not_owner(
    make_lock: Callable[..., DatabaseLock],
) -> None:
    lock = make_lock(owner="owner-1")
    other = make_lock(owner="owner-2")

    lock.acquire(blocking=False)

    assert other.refresh(ttl=3600) is False


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_refresh_returns_false_when_lock_not_held(lock: DatabaseLock) -> None:
    assert lock.refresh(ttl=3600) is False


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_auto_refresh_keeps_lock_alive(
    make_lock: Callable[..., DatabaseLock], db: DatabaseManager, name: str
) -> None:
    lock = make_lock(owner="owner-1", ttl=2, refresh=True)

    lock.acquire(blocking=False)

    with db.connection(name) as conn:
        row = conn.execute(
            lock._table.select().where(lock._table.c.key == "test-lock")
        ).first()
    original_expiration = row[2]

    time.sleep(1.5)

    with db.connection(name) as conn:
        row = conn.execute(
            lock._table.select().where(lock._table.c.key == "test-lock")
        ).first()

    assert row[2] >= original_expiration

    lock.release()


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_get_current_owner_returns_owner_when_held(lock: DatabaseLock) -> None:
    lock.acquire(blocking=False)

    assert lock.get_current_owner() == lock.owner


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_get_current_owner_returns_none_when_free(lock: DatabaseLock) -> None:
    assert lock.get_current_owner() is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_is_owned_by_current_process_returns_true_when_held(
    lock: DatabaseLock,
) -> None:
    lock.acquire(blocking=False)

    assert lock.is_owned_by_current_process() is True


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
def test_is_owned_by_current_process_returns_false_when_not_held(
    lock: DatabaseLock,
) -> None:
    assert lock.is_owned_by_current_process() is False
