import pytest

from sqlalchemy import URL
from sqlalchemy.util import immutabledict
from treat.mock import Mockery

from expanse.asynchronous.core.application import Application
from expanse.asynchronous.database import database_manager
from expanse.asynchronous.database.connection import Connection
from expanse.asynchronous.database.database_manager import DatabaseManager
from expanse.asynchronous.database.session import Session
from expanse.common.configuration.config import Config
from expanse.common.database._utils import create_engine


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
                    },
                }
            }
        )
    )

    return DatabaseManager(app)


async def test_database_manager_can_retrieve_a_default_connection(
    manager: DatabaseManager,
):
    assert isinstance(manager.connection(), Connection)


def test_database_manager_can_retrieve_a_default_session(manager: DatabaseManager):
    assert isinstance(manager.session(), Session)


def test_database_manager_can_retrieve_a_named_connection(
    manager: DatabaseManager,
):
    assert isinstance(manager.connection("another_sqlite"), Connection)


def test_database_manager_can_retrieve_a_named_session(manager: DatabaseManager):
    assert isinstance(manager.session("another_sqlite"), Session)


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
    ],
)
async def test_database_manager_builds_a_correct_engine_url(
    manager: DatabaseManager,
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
