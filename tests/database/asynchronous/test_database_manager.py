import re

from typing import Any

import pytest

from sqlalchemy import URL
from sqlalchemy import create_engine
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.util import immutabledict
from treat.mock import Mockery

from expanse.configuration.config import Config
from expanse.core.application import Application
from expanse.database.asynchronous import database_manager
from expanse.database.asynchronous.connection import AsyncConnection
from expanse.database.database_manager import AsyncDatabaseManager
from expanse.database.exceptions import UnconfiguredDatabaseDriverError
from expanse.database.exceptions import UnconfiguredDatabaseError
from expanse.database.exceptions import UnsupportedDatabaseDriverError
from expanse.database.session import AsyncSession


@pytest.fixture()
def manager() -> AsyncDatabaseManager:
    app = Application()
    app.set_config(
        Config(
            {
                "database": {
                    "default": "sqlite",
                    "connections": {
                        "sqlite": {"driver": "sqlite", "database": ":memory:"},
                        "another_sqlite": {"driver": "sqlite", "url": "sqlite://"},
                        "postgresql": {
                            "driver": "postgresql",
                            "host": "127.0.0.1",
                            "port": 5432,
                            "database": "expanse",
                            "username": "postgres",
                            "password": "password",
                        },
                        "postgresql_psycopg": {
                            "driver": "postgresql",
                            "dbapi": "psycopg",
                            "host": "127.0.0.1",
                            "port": 5432,
                            "database": "expanse",
                            "username": "postgres",
                            "password": "password",
                            "sslmode": "prefer",
                        },
                        "postgresql_asyncpg": {
                            "driver": "postgresql",
                            "url": "postgresql+asyncpg://postgres:password@127.0.0.1:5432/expanse",
                        },
                        "mysql": {
                            "driver": "mysql",
                            "host": "127.0.0.1",
                            "port": 3306,
                            "database": "expanse",
                            "username": "root",
                            "password": "password",
                        },
                        "mysql_asyncmy": {
                            "driver": "mysql",
                            "dbapi": "asyncmy",
                            "host": "127.0.0.1",
                            "database": "expanse",
                            "username": "root",
                            "password": "password",
                            "charset": "utf8mb4",
                        },
                        "mysql_aiomysql": {
                            "driver": "mysql",
                            "url": "mysql+aiomysql://root:password@127.0.0.1:3306/expanse?charset=utf8mb4",
                        },
                        "custom": {
                            "driver": "custom",
                            "url": "sqlite+aiosqlite://",
                        },
                        "undefined_driver": {
                            "database": ":memory:",
                        },
                    },
                }
            }
        )
    )

    return AsyncDatabaseManager(app)


async def test_database_manager_can_retrieve_a_default_connection(
    manager: AsyncDatabaseManager,
):
    assert isinstance(manager.connection(), AsyncConnection)


def test_database_manager_can_retrieve_a_default_session(manager: AsyncDatabaseManager):
    assert isinstance(manager.session(), AsyncSession)


def test_database_manager_can_retrieve_a_named_connection(
    manager: AsyncDatabaseManager,
):
    assert isinstance(manager.connection("another_sqlite"), AsyncConnection)


def test_database_manager_can_retrieve_a_named_session(manager: AsyncDatabaseManager):
    assert isinstance(manager.session("another_sqlite"), AsyncSession)


def test_database_manager_raises_when_retrieving_undefined_connection(
    manager: AsyncDatabaseManager,
):
    with pytest.raises(
        UnconfiguredDatabaseError,
        match=re.escape(
            r"The database connection [undefined_connection] is not configured."
        ),
    ):
        manager.connection("undefined_connection")


def test_database_manager_raises_when_retrieving_undefined_session(
    manager: AsyncDatabaseManager,
):
    with pytest.raises(
        UnconfiguredDatabaseError,
        match=re.escape(
            r"The database connection [undefined_connection] is not configured."
        ),
    ):
        manager.session("undefined_connection")


def test_database_manager_raises_when_retrieving_connection_with_undefined_driver(
    manager: AsyncDatabaseManager,
):
    with pytest.raises(
        UnconfiguredDatabaseDriverError,
        match=re.escape(
            r"The database connection [undefined_driver] does not specify a driver."
        ),
    ):
        manager.connection("undefined_driver")


def test_database_manager_raises_when_retrieving_session_with_undefined_driver(
    manager: AsyncDatabaseManager,
):
    with pytest.raises(
        UnconfiguredDatabaseDriverError,
        match=re.escape(
            r"The database connection [undefined_driver] does not specify a driver."
        ),
    ):
        manager.session("undefined_driver")


def test_database_manager_raises_when_retrieving_connection_with_unsupported_driver(
    manager: AsyncDatabaseManager,
):
    with pytest.raises(
        UnsupportedDatabaseDriverError,
        match=re.escape(
            r"The database connection [custom] specifies an unsupported driver [custom]."
        ),
    ):
        manager.connection("custom")


def test_database_manager_raises_when_retrieving_session_with_unsupported_driver(
    manager: AsyncDatabaseManager,
):
    with pytest.raises(
        UnsupportedDatabaseDriverError,
        match=re.escape(
            r"The database connection [custom] specifies an unsupported driver [custom]."
        ),
    ):
        manager.session("custom")


def test_database_manager_can_be_extended_with_custom_driver(
    manager: AsyncDatabaseManager,
):
    def create_mariadb_engine(
        db: AsyncDatabaseManager, name: str, config: dict[str, Any]
    ) -> AsyncEngine:
        url = config["url"]
        url = make_url(str(config["url"]))

        return db.create_base_engine(url)

    manager.extend("custom", create_mariadb_engine)

    engine = manager.configure_engine("custom")
    assert engine.dialect.name == "sqlite"


@pytest.mark.parametrize(
    "connection_name,expected_url",
    [
        (
            "sqlite",
            URL(
                drivername="sqlite+aiosqlite",
                database=":memory:",
                host=None,
                port=None,
                username=None,
                password=None,
                query=immutabledict(),
            ),
        ),
        (
            "another_sqlite",
            URL(
                drivername="sqlite+aiosqlite",
                database=None,
                host=None,
                port=None,
                username=None,
                password=None,
                query=immutabledict(),
            ),
        ),
        (
            "postgresql",
            URL(
                drivername="postgresql+psycopg_async",
                database="expanse",
                host="127.0.0.1",
                port=5432,
                username="postgres",
                password="password",
                query=immutabledict(),
            ),
        ),
        (
            "postgresql_psycopg",
            URL(
                drivername="postgresql+psycopg_async",
                database="expanse",
                host="127.0.0.1",
                port=5432,
                username="postgres",
                password="password",
                query=immutabledict({"sslmode": "prefer"}),
            ),
        ),
        (
            "postgresql_asyncpg",
            URL(
                drivername="postgresql+asyncpg",
                database="expanse",
                host="127.0.0.1",
                port=5432,
                username="postgres",
                password="password",
                query=immutabledict(),
            ),
        ),
        (
            "mysql",
            URL(
                drivername="mysql+asyncmy",
                database="expanse",
                host="127.0.0.1",
                port=3306,
                username="root",
                password="password",
                query=immutabledict({"charset": "utf8mb4"}),
            ),
        ),
        (
            "mysql_asyncmy",
            URL(
                drivername="mysql+asyncmy",
                database="expanse",
                host="127.0.0.1",
                port=3306,
                username="root",
                password="password",
                query=immutabledict({"charset": "utf8mb4"}),
            ),
        ),
        (
            "mysql_aiomysql",
            URL(
                drivername="mysql+aiomysql",
                database="expanse",
                host="127.0.0.1",
                port=3306,
                username="root",
                password="password",
                query=immutabledict({"charset": "utf8mb4"}),
            ),
        ),
    ],
)
async def test_database_manager_builds_a_correct_engine_url(
    manager: AsyncDatabaseManager,
    connection_name: str,
    expected_url: str,
    mockery: Mockery,
):
    # Create a valid engine first
    engine = create_engine("sqlite+aiosqlite://")
    mockery.mock(database_manager).should_receive("create_engine").times(1).with_(
        expected_url
    ).and_return(engine)

    await manager.connection(connection_name)
