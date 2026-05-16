from __future__ import annotations

import pickle
import time

from typing import TYPE_CHECKING

import pytest

from expanse.cache.config.database import DatabaseStoreConfig
from expanse.cache.synchronous.stores.database.store import DatabaseStore
from expanse.database.synchronous.database_manager import DatabaseManager


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

    db = await app.container.get(DatabaseManager)

    return DatabaseStore(DatabaseStoreConfig(connection=name), db)


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_set_stores_value(store: DatabaseStore) -> None:
    result = store.set("key", "value")

    assert result is True
    assert store.get("key") == "value"


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_set_overwrites_existing_value(store: DatabaseStore) -> None:
    store.set("key", "original")
    store.set("key", "updated")

    assert store.get("key") == "updated"


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_set_stores_complex_value(store: DatabaseStore) -> None:
    value = {"nested": [1, 2, 3], "flag": True}

    store.set("key", value)

    assert store.get("key") == value


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_set_with_ttl_stores_value(store: DatabaseStore) -> None:
    result = store.set("key", "value", ttl=60)

    assert result is True
    assert store.get("key") == "value"


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_get_returns_none_for_missing_key(store: DatabaseStore) -> None:
    assert store.get("missing") is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_get_returns_none_for_expired_key(
    store: DatabaseStore,
    app: Application,
    name: str,
) -> None:
    db = await app.container.get(DatabaseManager)

    with db.connection(name) as connection:
        connection.execute(
            store._table.insert().values(
                {
                    "key": "expired",
                    "data": pickle.dumps("stale value"),
                    "expiration": int(time.time()) - 1,
                }
            )
        )
        connection.commit()

    assert store.get("expired") is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_get_returns_value_with_no_expiration(
    store: DatabaseStore,
    app: Application,
    name: str,
) -> None:
    db = await app.container.get(DatabaseManager)

    with db.connection(name) as connection:
        connection.execute(
            store._table.insert().values(
                {
                    "key": "persistent",
                    "data": pickle.dumps("persistent value"),
                    "expiration": None,
                }
            )
        )
        connection.commit()

    assert store.get("persistent") == "persistent value"


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_expired_entries_are_deleted_on_read(
    store: DatabaseStore,
    app: Application,
    name: str,
) -> None:
    db = await app.container.get(DatabaseManager)

    with db.connection(name) as connection:
        connection.execute(
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
        connection.commit()

    store.get_many(["valid", "expired"])

    with db.connection(name) as connection:
        row = connection.execute(
            store._table.select().where(store._table.c.key == "expired")
        ).first()

    assert row is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_set_many_stores_multiple_values(store: DatabaseStore) -> None:
    result = store.set_many({"a": 1, "b": 2, "c": 3})

    assert result is True
    assert store.get("a") == 1
    assert store.get("b") == 2
    assert store.get("c") == 3


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_get_many_returns_values_for_existing_keys(store: DatabaseStore) -> None:
    store.set_many({"x": 10, "y": 20})

    result = store.get_many(["x", "y"])

    assert result == {"x": 10, "y": 20}


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_get_many_returns_none_for_missing_keys(store: DatabaseStore) -> None:
    store.set("x", 10)

    result = store.get_many(["x", "missing"])

    assert result == {"x": 10, "missing": None}


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_get_many_returns_empty_dict_for_empty_keys(
    store: DatabaseStore,
) -> None:
    result = store.get_many([])

    assert result == {}


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_has_returns_true_for_existing_key(store: DatabaseStore) -> None:
    store.set("key", "value")

    assert store.has("key") is True


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_has_returns_false_for_missing_key(store: DatabaseStore) -> None:
    assert store.has("missing") is False


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_has_returns_false_for_expired_key(
    store: DatabaseStore,
    app: Application,
    name: str,
) -> None:
    db = await app.container.get(DatabaseManager)

    with db.connection(name) as connection:
        connection.execute(
            store._table.insert().values(
                {
                    "key": "expired",
                    "data": pickle.dumps("stale"),
                    "expiration": int(time.time()) - 1,
                }
            )
        )
        connection.commit()

    assert store.has("expired") is False


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_delete_removes_key(store: DatabaseStore) -> None:
    store.set("key", "value")

    result = store.delete("key")

    assert result is True
    assert store.get("key") is None


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_delete_returns_true_for_missing_key(store: DatabaseStore) -> None:
    result = store.delete("missing")

    assert result is True


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_clear_removes_all_entries(store: DatabaseStore) -> None:
    store.set_many({"a": 1, "b": 2})

    result = store.clear()

    assert result is True
    assert store.get("a") is None
    assert store.get("b") is None


@pytest.mark.usefixtures("setup_databases")
async def test_set_works_for_non_natively_supported_dialect(
    app: Application, command_tester: CommandTester, mockery: Mockery
) -> None:
    app.config["database"]["default"] = "sqlite"

    command_tester.command("db migrate").run()

    db = await app.container.get(DatabaseManager)
    db.configure_engine("sqlite")

    from sqlalchemy.dialects.sqlite.base import SQLiteDialect

    mockery.mock(SQLiteDialect).should_receive("name").and_return("not_sqlite")

    store = DatabaseStore(DatabaseStoreConfig(connection="sqlite"), db)

    store.set("key", "value")

    assert store.get("key") == "value"


@pytest.mark.usefixtures("setup_databases")
async def test_upsert_works_for_non_natively_supported_dialect(
    app: Application, command_tester: CommandTester, mockery: Mockery
) -> None:
    app.config["database"]["default"] = "sqlite"

    command_tester.command("db migrate").run()

    db = await app.container.get(DatabaseManager)
    db.configure_engine("sqlite")

    from sqlalchemy.dialects.sqlite.base import SQLiteDialect

    mockery.mock(SQLiteDialect).should_receive("name").and_return("not_sqlite")

    store = DatabaseStore(DatabaseStoreConfig(connection="sqlite"), db)

    store.set("key", "original")
    store.set("key", "updated")

    assert store.get("key") == "updated"
