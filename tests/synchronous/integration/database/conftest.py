from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from expanse.core.application import Application
from expanse.database.database_manager import DatabaseManager


@pytest.fixture(autouse=True)
def setup_databases(app: Application, tmp_path: Path) -> Generator[None]:
    config: dict[str, dict[str, Any]] = app.container.get("config")

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
                "url": "postgresql://postgres:password@localhost:5432/expanse",
            },
            "postgresql_psycopg2": {
                "driver": "postgresql",
                "url": "postgresql+psycopg2://postgres:password@localhost:5432/expanse",
            },
            "postgresql_psycopg": {
                "driver": "postgresql",
                "url": "postgresql+psycopg://postgres:password@localhost:5432/expanse",
            },
            "postgresql_pg8000": {
                "driver": "postgresql",
                "url": "postgresql+pg8000://postgres:password@localhost:5432/expanse",
            },
            "test": {"driver": "sqlite", "database": tmp_path.joinpath("test.sqlite")},
        },
    }

    db = app.container.get(DatabaseManager)

    with db.connection("sqlite") as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS my_table (id INTEGER)")
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
        connection.execute("CREATE TABLE IF NOT EXISTS my_table (id INTEGER)")
        connection.execute("INSERT INTO my_table (id) VALUES (:id)", {"id": "sqlite2"})
        connection.commit()

    with db.connection("postgresql") as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS my_table (id VARCHAR)")
        connection.execute(
            "INSERT INTO my_table (id) VALUES (:id)",
            [
                {"id": "postgresql"},
                {"id": "postgresql_psycopg2"},
                {"id": "postgresql_psycopg"},
                {"id": "postgresql_pg8000"},
            ],
        )
        connection.commit()

    yield

    with db.connection("postgresql") as connection:
        connection.execute("DROP TABLE IF EXISTS my_table")
