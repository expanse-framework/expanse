import re

from typing import Any

import pytest

from sqlalchemy import URL
from sqlalchemy import Engine
from sqlalchemy import create_engine
from sqlalchemy import make_url
from sqlalchemy.orm import Session
from sqlalchemy.util import immutabledict
from treat.mock import Mockery

from expanse.configuration.config import Config
from expanse.core.application import Application
from expanse.database.database_manager import DatabaseManager
from expanse.database.exceptions import UnconfiguredDatabaseDriverError
from expanse.database.exceptions import UnconfiguredDatabaseError
from expanse.database.exceptions import UnsupportedDatabaseDriverError
from expanse.database.synchronous import database_manager
from expanse.database.synchronous.connection import Connection


@pytest.fixture()
def manager() -> DatabaseManager:
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
                        "postgresql_psycopg2": {
                            "driver": "postgresql",
                            "dbapi": "psycopg2",
                            "host": "127.0.0.1",
                            "database": "expanse",
                            "username": "postgres",
                            "password": "password",
                            "sslmode": "prefer",
                        },
                        "postgresql_psycopg": {
                            "driver": "postgresql",
                            "url": "postgresql+psycopg://postgres:password@localhost:5432/expanse",
                        },
                        "postgresql_pg8000": {
                            "driver": "postgresql",
                            "url": "postgresql+pg8000://postgres:password@localhost:5432/expanse",
                        },
                        "mysql": {
                            "driver": "mysql",
                            "host": "127.0.0.1",
                            "port": 3306,
                            "database": "expanse",
                            "username": "root",
                            "password": "password",
                        },
                        "mysql_pymysql": {
                            "driver": "mysql",
                            "dbapi": "pymysql",
                            "host": "127.0.0.1",
                            "database": "expanse",
                            "username": "root",
                            "password": "password",
                            "charset": "utf8mb4",
                        },
                        "mysql_mysqldb": {
                            "driver": "mysql",
                            "url": "mysql+mysqldb://root:password@127.0.0.1:3306/expanse?charset=utf8mb4",
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

    return DatabaseManager(app)


def test_database_manager_can_retrieve_a_default_connection(manager: DatabaseManager):
    assert isinstance(manager.connection(), Connection)


def test_database_manager_can_retrieve_a_default_session(manager: DatabaseManager):
    assert isinstance(manager.session(), Session)


def test_database_manager_can_retrieve_a_named_connection(manager: DatabaseManager):
    assert isinstance(manager.connection("another_sqlite"), Connection)


def test_database_manager_can_retrieve_a_named_session(manager: DatabaseManager):
    assert isinstance(manager.session("another_sqlite"), Session)


def test_database_manager_raises_when_retrieving_undefined_connection(
    manager: DatabaseManager,
):
    with pytest.raises(
        UnconfiguredDatabaseError,
        match=re.escape(
            r"The database connection [undefined_connection] is not configured."
        ),
    ):
        manager.connection("undefined_connection")


def test_database_manager_raises_when_retrieving_undefined_session(
    manager: DatabaseManager,
):
    with pytest.raises(
        UnconfiguredDatabaseError,
        match=re.escape(
            r"The database connection [undefined_connection] is not configured."
        ),
    ):
        manager.session("undefined_connection")


def test_database_manager_raises_when_retrieving_connection_with_undefined_driver(
    manager: DatabaseManager,
):
    with pytest.raises(
        UnconfiguredDatabaseDriverError,
        match=re.escape(
            r"The database connection [undefined_driver] does not specify a driver."
        ),
    ):
        manager.connection("undefined_driver")


def test_database_manager_raises_when_retrieving_session_with_undefined_driver(
    manager: DatabaseManager,
):
    with pytest.raises(
        UnconfiguredDatabaseDriverError,
        match=re.escape(
            r"The database connection [undefined_driver] does not specify a driver."
        ),
    ):
        manager.session("undefined_driver")


def test_database_manager_raises_when_retrieving_connection_with_unsupported_driver(
    manager: DatabaseManager,
):
    with pytest.raises(
        UnsupportedDatabaseDriverError,
        match=re.escape(
            r"The database connection [custom] specifies an unsupported driver [custom]."
        ),
    ):
        manager.connection("custom")


def test_database_manager_raises_when_retrieving_session_with_unsupported_driver(
    manager: DatabaseManager,
):
    with pytest.raises(
        UnsupportedDatabaseDriverError,
        match=re.escape(
            r"The database connection [custom] specifies an unsupported driver [custom]."
        ),
    ):
        manager.session("custom")


def test_database_manager_can_be_extended_with_custom_driver(
    manager: DatabaseManager,
):
    def create_custom_engine(
        db: DatabaseManager, name: str, config: dict[str, Any]
    ) -> Engine:
        url = config["url"]
        url = make_url(str(config["url"]))

        return db.create_base_engine(url)

    manager.extend("custom", create_custom_engine)

    engine = manager.configure_engine("custom")
    assert engine.dialect.name == "sqlite"


@pytest.mark.parametrize(
    "connection_name,expected_url",
    [
        (
            "sqlite",
            URL(
                drivername="sqlite",
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
                drivername="sqlite",
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
                drivername="postgresql",
                database="expanse",
                host="127.0.0.1",
                port=5432,
                username="postgres",
                password="password",
                query=immutabledict(),
            ),
        ),
        (
            "postgresql_psycopg2",
            URL(
                drivername="postgresql+psycopg2",
                database="expanse",
                host="127.0.0.1",
                port=5432,
                username="postgres",
                password="password",
                query=immutabledict({"sslmode": "prefer"}),
            ),
        ),
        (
            "postgresql_psycopg",
            URL(
                drivername="postgresql+psycopg",
                database="expanse",
                host="localhost",
                port=5432,
                username="postgres",
                password="password",
                query=immutabledict(),
            ),
        ),
        (
            "postgresql_pg8000",
            URL(
                drivername="postgresql+pg8000",
                database="expanse",
                host="localhost",
                port=5432,
                username="postgres",
                password="password",
                query=immutabledict(),
            ),
        ),
        (
            "mysql",
            URL(
                drivername="mysql",
                database="expanse",
                host="127.0.0.1",
                port=3306,
                username="root",
                password="password",
                query=immutabledict({"charset": "utf8mb4"}),
            ),
        ),
        (
            "mysql_pymysql",
            URL(
                drivername="mysql+pymysql",
                database="expanse",
                host="127.0.0.1",
                port=3306,
                username="root",
                password="password",
                query=immutabledict({"charset": "utf8mb4"}),
            ),
        ),
        (
            "mysql_mysqldb",
            URL(
                drivername="mysql+mysqldb",
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
def test_database_manager_builds_a_correct_engine_url(
    manager: DatabaseManager, connection_name: str, expected_url: str, mockery: Mockery
):
    # Create a valid engine first
    engine = create_engine("sqlite://")
    mockery.mock(database_manager).should_receive("create_engine").times(1).with_(
        expected_url
    ).and_return(engine)

    manager.connection(connection_name)
