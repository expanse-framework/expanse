from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest

from expanse.asynchronous.core.application import Application
from expanse.asynchronous.database.database_manager import DatabaseManager


@pytest.fixture(autouse=True)
async def setup_databases(app: Application, tmp_path: Path) -> AsyncGenerator[None]:
    config: dict[str, dict[str, Any]] = await app.container.get("config")

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
                "url": "postgresql://postgres:password@127.0.0.1:5432/expanse",
            },
            "postgresql_psycopg": {
                "driver": "postgresql",
                "url": "postgresql+psycopg://postgres:password@127.0.0.1:5432/expanse",
            },
            "postgresql_asyncpg": {
                "driver": "postgresql",
                "url": "postgresql+asyncpg://postgres:password@127.0.0.1:5432/expanse",
            },
            "test": {"driver": "sqlite", "database": tmp_path.joinpath("test.sqlite")},
        },
    }

    db = await app.container.get(DatabaseManager)

    async with db.connection("sqlite") as connection:
        await connection.execute("CREATE TABLE IF NOT EXISTS my_table (id VARCHAR)")
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER NOT NULL,
                first_name VARCHAR NOT NULL,
                last_name VARCHAR,
                email VARCHAR NOT NULL,
                PRIMARY KEY (id)
            );"""
        )
        await connection.execute(
            "INSERT INTO my_table (id) VALUES (:id)", {"id": "sqlite"}
        )
        await connection.execute(
            "INSERT INTO users (first_name, last_name, email) VALUES ('John', 'Doe', 'john@doe.com')"
        )
        await connection.commit()

    async with db.connection("sqlite2") as connection:
        await connection.execute("CREATE TABLE IF NOT EXISTS my_table (id VARCHAR)")
        await connection.execute(
            "INSERT INTO my_table (id) VALUES (:id)", {"id": "sqlite2"}
        )
        await connection.commit()

    async with db.connection("postgresql") as connection:
        await connection.execute("CREATE TABLE IF NOT EXISTS my_table (id VARCHAR)")
        await connection.execute(
            "INSERT INTO my_table (id) VALUES (:id)",
            [
                {"id": "postgresql"},
                {"id": "postgresql_psycopg"},
                {"id": "postgresql_asyncpg"},
            ],
        )
        await connection.commit()

    yield

    async with db.connection("postgresql") as connection:
        await connection.execute("DROP TABLE IF EXISTS my_table")
