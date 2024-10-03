import os

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from expanse.core.application import Application
from expanse.database.database_manager import AsyncDatabaseManager


if TYPE_CHECKING:
    from expanse.configuration.config import Config

pytestmark = pytest.mark.db


@pytest.fixture(autouse=True)
async def setup_additional_databases(
    app: Application, tmp_path: Path
) -> AsyncGenerator[None]:
    config: Config = app.config

    config["database"]["connections"].update(
        {
            "postgresql_psycopg": {
                "driver": "postgresql",
                "url": f"postgresql+psycopg://postgres:password@127.0.0.1:{os.getenv('POSTGRES_TEST_PORT', 5432)}/expanse",
            },
            "postgresql_asyncpg": {
                "driver": "postgresql",
                "url": f"postgresql+asyncpg://postgres:password@127.0.0.1:{os.getenv('POSTGRES_TEST_PORT', 5432)}/expanse",
            },
            "mysql_asyncmy": {
                "driver": "mysql",
                "url": f"mysql+asyncmy://root:password@127.0.0.1:{os.getenv('MYSQL_TEST_PORT', 3306)}/expanse",
            },
            "mysql_aiomysql": {
                "driver": "mysql",
                "url": f"mysql+aiomysql://root:password@127.0.0.1:{os.getenv('MYSQL_TEST_PORT', 3306)}/expanse",
            },
        }
    )

    db = await app.container.get(AsyncDatabaseManager)

    async with db.connection("postgresql") as connection:
        await connection.execute(
            "INSERT INTO my_table (id) VALUES (:id)",
            [
                {"id": "postgresql_psycopg"},
                {"id": "postgresql_asyncpg"},
            ],
        )
        await connection.commit()

    async with db.connection("mysql") as connection:
        await connection.execute(
            "INSERT INTO my_table (id) VALUES (:id)",
            [
                {"id": "mysql_asyncmy"},
                {"id": "mysql_aiomysql"},
            ],
        )
        await connection.commit()

    yield
