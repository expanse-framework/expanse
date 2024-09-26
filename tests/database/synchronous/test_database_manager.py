import pytest

from sqlalchemy import URL
from sqlalchemy.orm import Session
from sqlalchemy.util import immutabledict
from treat.mock import Mockery

from expanse.configuration.config import Config
from expanse.core.application import Application
from expanse.database._utils import create_engine
from expanse.database.connection import Connection
from expanse.database.database_manager import DatabaseManager
from expanse.database.engine import Engine
from expanse.database.synchronous import database_manager


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
    engine = create_engine("sqlite://", engine_class=Engine)
    mockery.mock(database_manager).should_receive("create_engine").times(1).with_(
        expected_url, engine_class=Engine
    ).and_return(engine)

    manager.connection(connection_name)
