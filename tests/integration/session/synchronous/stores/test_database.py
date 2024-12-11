import base64
import json

from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pytest

from treat.mock.mockery import Mockery

from expanse.core.application import Application
from expanse.database.synchronous.database_manager import DatabaseManager
from expanse.session.synchronous.stores.database import DatabaseStore
from expanse.testing.command_tester import CommandTester


pytestmark = pytest.mark.db


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_store_can_read_from_the_database(
    app: Application, name: str, command_tester: CommandTester
) -> None:
    session_id = "s" * 40

    app.config["database"]["default"] = name

    command = command_tester.command("db migrate")
    command.run()

    db = await app.container.get(DatabaseManager)

    store = DatabaseStore(db, "sessions", 1200, database_name=name)

    with db.connection(name) as connection:
        connection.execute(
            store._table.insert().values(
                {
                    "id": session_id,
                    "ip_address": "127.0.0.1",
                    "user_agent": "Mozilla/5.0",
                    "payload": base64.b64encode(
                        json.dumps({"foo": "bar"}).encode()
                    ).decode(),
                    "last_activity": datetime.now(timezone.utc),
                }
            )
        )
        connection.commit()

    assert store.read(session_id) == json.dumps({"foo": "bar"})


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_store_can_write_to_the_database(
    app: Application, name: str, command_tester: CommandTester
) -> None:
    session_id = "s" * 40

    app.config["database"]["default"] = name

    command = command_tester.command("db migrate")
    command.run()

    db = await app.container.get(DatabaseManager)

    store = DatabaseStore(db, "sessions", 120, database_name=name)

    with db.connection(name) as connection:
        connection.execute(
            store._table.insert().values(
                {
                    "id": session_id,
                    "ip_address": "127.0.0.1",
                    "user_agent": "Mozilla/5.0",
                    "payload": base64.b64encode(
                        json.dumps({"foo": "bar"}).encode()
                    ).decode(),
                    "last_activity": datetime.now(timezone.utc),
                }
            )
        )
        connection.commit()

    store.write(session_id, json.dumps({"bar": "baz"}))

    with db.connection(name) as connection:
        row = connection.execute(
            store._table.select().where(store._table.c.id == session_id)
        ).first()

    assert row is not None
    assert row.id == session_id
    assert row.ip_address == "127.0.0.1"
    assert row.user_agent == "Mozilla/5.0"
    assert row.payload == base64.b64encode(json.dumps({"bar": "baz"}).encode()).decode()


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_store_can_delete_from_the_database(
    app: Application, name: str, command_tester: CommandTester
) -> None:
    session_id = "s" * 40

    app.config["database"]["default"] = name

    command = command_tester.command("db migrate")
    command.run()

    db = await app.container.get(DatabaseManager)

    store = DatabaseStore(db, "sessions", 120, database_name=name)

    with db.connection(name) as connection:
        connection.execute(
            store._table.insert().values(
                {
                    "id": session_id,
                    "ip_address": "127.0.0.1",
                    "user_agent": "Mozilla/5.0",
                    "payload": base64.b64encode(
                        json.dumps({"foo": "bar"}).encode()
                    ).decode(),
                    "last_activity": datetime.now(timezone.utc),
                }
            )
        )
        connection.commit()

    store.delete(session_id)

    with db.connection(name) as connection:
        row = connection.execute(
            store._table.select().where(store._table.c.id == session_id)
        ).first()

    assert row is None


@pytest.mark.usefixtures("setup_databases")
async def test_writing_to_store_works_for_non_natively_supported_dialect(
    app: Application, command_tester: CommandTester, mockery: Mockery
) -> None:
    session_id = "s" * 40

    app.config["database"]["default"] = "sqlite"

    command = command_tester.command("db migrate")
    command.run()

    db = await app.container.get(DatabaseManager)
    db.configure_engine("sqlite")

    from sqlalchemy.dialects.sqlite.base import SQLiteDialect

    mockery.mock(SQLiteDialect).should_receive("name").and_return("not_sqlite")

    store = DatabaseStore(db, "sessions", 120, database_name="sqlite")

    with db.connection("sqlite") as connection:
        connection.execute(
            store._table.insert().values(
                {
                    "id": session_id,
                    "ip_address": "127.0.0.1",
                    "user_agent": "Mozilla/5.0",
                    "payload": base64.b64encode(
                        json.dumps({"foo": "bar"}).encode()
                    ).decode(),
                    "last_activity": datetime.now(timezone.utc),
                }
            )
        )
        connection.commit()

    store.write(session_id, json.dumps({"bar": "baz"}))

    with db.connection("sqlite") as connection:
        row = connection.execute(
            store._table.select().where(store._table.c.id == session_id)
        ).first()

    assert row is not None
    assert row.id == session_id
    assert row.ip_address == "127.0.0.1"
    assert row.user_agent == "Mozilla/5.0"
    assert row.payload == base64.b64encode(json.dumps({"bar": "baz"}).encode()).decode()


@pytest.mark.usefixtures("setup_databases")
@pytest.mark.parametrize("name", ["sqlite", "postgresql", "mysql"])
async def test_expired_sessions_can_be_cleared(
    app: Application, name: str, command_tester: CommandTester, mockery: Mockery
) -> None:
    session_id = "s" * 40
    app.config["database"]["default"] = name

    command = command_tester.command("db migrate")
    command.run()

    db = await app.container.get(DatabaseManager)

    store = DatabaseStore(db, "sessions", 120, database_name=name)

    with db.connection(name) as connection:
        connection.execute(
            store._table.insert().values(
                [
                    {
                        "id": session_id,
                        "ip_address": "127.0.0.1",
                        "user_agent": "Mozilla/5.0",
                        "payload": base64.b64encode(
                            json.dumps({"foo": "bar"}).encode()
                        ).decode(),
                        "last_activity": datetime.now(timezone.utc),
                    },
                    {
                        "id": "t" * 40,
                        "ip_address": "127.0.0.1",
                        "user_agent": "Mozilla/5.0",
                        "payload": base64.b64encode(
                            json.dumps({"foo": "bar"}).encode()
                        ).decode(),
                        "last_activity": datetime.now(timezone.utc)
                        - timedelta(minutes=180),
                    },
                ]
            )
        )
        connection.commit()

    assert store.clear() == 1
    assert store.clear() == 0

    assert store.read(session_id) != ""
    assert store.read("t" * 40) == ""
