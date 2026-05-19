from __future__ import annotations

import pickle
import time

from typing import TYPE_CHECKING

import pytest

from expanse.cache.asynchronous.stores.database.store import DatabaseStore
from expanse.cache.config.database import DatabaseStoreConfig
from expanse.database.asynchronous.database_manager import AsyncDatabaseManager


if TYPE_CHECKING:
    from treat.mock.mockery import Mockery

    from expanse.core.application import Application
    from expanse.testing.command_tester import CommandTester


pytestmark = pytest.mark.db


@pytest.fixture()
async def store(
    app: Application, name: str, command_tester: CommandTester
) -> DatabaseStore:
    app.config["database"]["default"] = name

    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)

    return DatabaseStore(DatabaseStoreConfig(connection=name), db)


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_set_stores_value(store: DatabaseStore) -> None:
    result = await store.set("key", "value")

    assert result is True
    assert await store.get("key") == "value"


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_set_overwrites_existing_value(store: DatabaseStore) -> None:
    await store.set("key", "original")
    await store.set("key", "updated")

    assert await store.get("key") == "updated"


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_set_stores_complex_value(store: DatabaseStore) -> None:
    value = {"nested": [1, 2, 3], "flag": True}

    await store.set("key", value)

    assert await store.get("key") == value


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_set_with_ttl_stores_value(store: DatabaseStore) -> None:
    result = await store.set("key", "value", ttl=60)

    assert result is True
    assert await store.get("key") == "value"


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_get_returns_none_for_missing_key(store: DatabaseStore) -> None:
    assert await store.get("missing") is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_get_returns_none_for_expired_key(
    store: DatabaseStore,
    app: Application,
    name: str,
) -> None:
    db = await app.container.get(AsyncDatabaseManager)

    async with db.connection(name) as connection:
        await connection.execute(
            store._table.insert().values(
                {
                    "key": "expired",
                    "data": pickle.dumps("stale value"),
                    "expiration": int(time.time()) - 1,
                }
            )
        )
        await connection.commit()

    assert await store.get("expired") is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_get_returns_value_with_no_expiration(
    store: DatabaseStore,
    app: Application,
    name: str,
) -> None:
    db = await app.container.get(AsyncDatabaseManager)

    async with db.connection(name) as connection:
        await connection.execute(
            store._table.insert().values(
                {
                    "key": "persistent",
                    "data": pickle.dumps("persistent value"),
                    "expiration": None,
                }
            )
        )
        await connection.commit()

    assert await store.get("persistent") == "persistent value"


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_expired_entries_are_deleted_on_read(
    store: DatabaseStore,
    app: Application,
    name: str,
) -> None:
    db = await app.container.get(AsyncDatabaseManager)

    async with db.connection(name) as connection:
        await connection.execute(
            store._table.insert().values(
                [
                    {
                        "key": "valid",
                        "data": pickle.dumps("valid value"),
                        "expiration": int(time.time()) + 3600,
                    },
                    {
                        "key": "expired",
                        "data": pickle.dumps("expired value"),
                        "expiration": int(time.time()) - 1,
                    },
                ]
            )
        )
        await connection.commit()

    await store.get_many(["valid", "expired"])

    async with db.connection(name) as connection:
        row = (
            await connection.execute(
                store._table.select().where(store._table.c.key == "expired")
            )
        ).first()

    assert row is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_set_many_stores_multiple_values(store: DatabaseStore) -> None:
    result = await store.set_many({"a": 1, "b": 2, "c": 3})

    assert result is True
    assert await store.get("a") == 1
    assert await store.get("b") == 2
    assert await store.get("c") == 3


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_get_many_returns_values_for_existing_keys(store: DatabaseStore) -> None:
    await store.set_many({"x": 10, "y": 20})

    result = await store.get_many(["x", "y"])

    assert result == {"x": 10, "y": 20}


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_get_many_returns_none_for_missing_keys(store: DatabaseStore) -> None:
    await store.set("x", 10)

    result = await store.get_many(["x", "missing"])

    assert result == {"x": 10, "missing": None}


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_get_many_returns_empty_dict_for_empty_keys(
    store: DatabaseStore,
) -> None:
    result = await store.get_many([])

    assert result == {}


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_has_returns_true_for_existing_key(store: DatabaseStore) -> None:
    await store.set("key", "value")

    assert await store.has("key") is True


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_has_returns_false_for_missing_key(store: DatabaseStore) -> None:
    assert await store.has("missing") is False


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_has_returns_false_for_expired_key(
    store: DatabaseStore,
    app: Application,
    name: str,
) -> None:
    db = await app.container.get(AsyncDatabaseManager)

    async with db.connection(name) as connection:
        await connection.execute(
            store._table.insert().values(
                {
                    "key": "expired",
                    "data": pickle.dumps("stale"),
                    "expiration": int(time.time()) - 1,
                }
            )
        )
        await connection.commit()

    assert await store.has("expired") is False


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_delete_removes_key(store: DatabaseStore) -> None:
    await store.set("key", "value")

    result = await store.delete("key")

    assert result is True
    assert await store.get("key") is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_delete_returns_true_for_missing_key(store: DatabaseStore) -> None:
    result = await store.delete("missing")

    assert result is True


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_clear_removes_all_entries(store: DatabaseStore) -> None:
    await store.set_many({"a": 1, "b": 2})

    result = await store.clear()

    assert result is True
    assert await store.get("a") is None
    assert await store.get("b") is None


@pytest.mark.usefixtures("setup_databases")
async def test_set_works_for_non_natively_supported_dialect(
    app: Application, command_tester: CommandTester, mockery: Mockery
) -> None:
    app.config["database"]["default"] = "sqlite"

    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    db.configure_engine("sqlite")

    from sqlalchemy.dialects.sqlite.base import SQLiteDialect

    mockery.mock(SQLiteDialect).should_receive("name").and_return("not_sqlite")

    store = DatabaseStore(DatabaseStoreConfig(connection="sqlite"), db)

    await store.set("key", "value")

    assert await store.get("key") == "value"


@pytest.mark.usefixtures("setup_databases")
async def test_upsert_works_for_non_natively_supported_dialect(
    app: Application, command_tester: CommandTester, mockery: Mockery
) -> None:
    app.config["database"]["default"] = "sqlite"

    command_tester.command("db migrate").run()

    db = await app.container.get(AsyncDatabaseManager)
    db.configure_engine("sqlite")

    from sqlalchemy.dialects.sqlite.base import SQLiteDialect

    mockery.mock(SQLiteDialect).should_receive("name").and_return("not_sqlite")

    store = DatabaseStore(DatabaseStoreConfig(connection="sqlite"), db)

    await store.set("key", "original")
    await store.set("key", "updated")

    assert await store.get("key") == "updated"


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_lock_acquire_and_release(store: DatabaseStore) -> None:
    lock = store.lock("test-lock", ttl=10)

    acquired = await lock.acquire(blocking=False)
    assert acquired is True

    released = await lock.release()
    assert released is True
