import os

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from expanse.core.application import Application
from expanse.database.database_manager import DatabaseManager


pytestmark = pytest.mark.db


@pytest.fixture(autouse=True)
async def setup_additional_databases(
    app: Application, tmp_path: Path
) -> AsyncGenerator[None]:
    app.config["database"]["connections"].update(
        {
            "postgresql_psycopg2": {
                "driver": "postgresql",
                "url": f"postgresql+psycopg2://postgres:password@localhost:{os.getenv('POSTGRES_TEST_PORT', 5432)}/expanse",
            },
            "postgresql_psycopg": {
                "driver": "postgresql",
                "url": f"postgresql+psycopg://postgres:password@localhost:{os.getenv('POSTGRES_TEST_PORT', 5432)}/expanse",
            },
            "postgresql_pg8000": {
                "driver": "postgresql",
                "url": f"postgresql+pg8000://postgres:password@localhost:{os.getenv('POSTGRES_TEST_PORT', 5432)}/expanse",
            },
            "mysql_pymysql": {
                "driver": "mysql",
                "url": f"mysql+pymysql://root:password@127.0.0.1:{os.getenv('MYSQL_TEST_PORT', 3306)}/expanse",
            },
            "mysql_mysqldb": {
                "driver": "mysql",
                "url": f"mysql+mysqldb://root:password@127.0.0.1:{os.getenv('MYSQL_TEST_PORT', 3306)}/expanse",
            },
        }
    )

    db = await app.container.get(DatabaseManager)

    with db.connection("postgresql") as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS my_table (id VARCHAR)")
        connection.execute(
            "INSERT INTO my_table (id) VALUES (:id)",
            [
                {"id": "postgresql_psycopg2"},
                {"id": "postgresql_psycopg"},
                {"id": "postgresql_pg8000"},
            ],
        )
        connection.commit()

    with db.connection("mysql") as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS my_table (id VARCHAR(255))")
        connection.execute(
            "INSERT INTO my_table (id) VALUES (:id)",
            [
                {"id": "mysql_pymysql"},
                {"id": "mysql_mysqldb"},
            ],
        )
        connection.commit()

    yield
