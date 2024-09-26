import pytest

from sqlalchemy import URL
from sqlalchemy.util import immutabledict
from treat.mock import Mockery

from expanse.configuration.config import Config
from expanse.core.application import Application
from expanse.database._utils import create_engine
from expanse.database.asynchronous import database_manager
from expanse.database.connection import AsyncConnection
from expanse.database.database_manager import AsyncDatabaseManager
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
