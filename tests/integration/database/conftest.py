import os

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from expanse.core.application import Application
from expanse.database.synchronous.database_manager import DatabaseManager


if TYPE_CHECKING:
    from expanse.configuration.config import Config

pytestmark = pytest.mark.db


@pytest.fixture(autouse=True)
async def setup_databases(app: Application, tmp_path: Path) -> AsyncGenerator[None]:
    config: Config = app.config

    config["database"] = {
        "default": "sqlite",
        "connections": {
            "sqlite": {"driver": "sqlite", "database": tmp_path.joinpath("db.sqlite")},
            "sqlite2": {
                "driver": "sqlite",
                "url": f"sqlite:///{tmp_path.joinpath('db2.sqlite').as_posix()}",
            },
            "postgresql": {
                "driver": "postgresql",
                "url": f"postgresql://postgres:password@127.0.0.1:{os.getenv('POSTGRES_TEST_PORT', 5432)}/expanse",
            },
            "mysql": {
                "driver": "mysql",
                "url": f"mysql://root:password@127.0.0.1:{os.getenv('MYSQL_TEST_PORT', 3306)}/expanse",
            },
            "test": {"driver": "sqlite", "database": tmp_path.joinpath("test.sqlite")},
        },
    }

    db = await app.container.get(DatabaseManager)

    with db.connection("sqlite") as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS my_table (id VARCHAR)")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER NOT NULL,
                first_name VARCHAR NOT NULL,
                last_name VARCHAR,
                email VARCHAR NOT NULL,
                PRIMARY KEY (id)
            );"""
        )
        connection.execute("INSERT INTO my_table (id) VALUES (:id)", {"id": "sqlite"})
        connection.execute(
            "INSERT INTO users (first_name, last_name, email) VALUES ('John', 'Doe', 'john@doe.com')"
        )
        connection.commit()

    with db.connection("sqlite2") as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS my_table (id VARCHAR)")
        connection.execute("INSERT INTO my_table (id) VALUES (:id)", {"id": "sqlite2"})
        connection.commit()

    with db.connection("postgresql") as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS my_table (id VARCHAR)")
        connection.execute(
            "INSERT INTO my_table (id) VALUES (:id)",
            [
                {"id": "postgresql"},
            ],
        )
        connection.commit()

    with db.connection("mysql") as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS my_table (id VARCHAR(255))")
        connection.execute(
            "INSERT INTO my_table (id) VALUES (:id)",
            [
                {"id": "mysql"},
            ],
        )
        connection.commit()

    yield

    with db.connection("postgresql") as connection:
        connection.execute("DROP TABLE IF EXISTS my_table")

    with db.connection("mysql") as connection:
        connection.execute("DROP TABLE IF EXISTS my_table")
