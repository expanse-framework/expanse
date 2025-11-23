from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from expanse.core.application import Application
from expanse.database.database_manager import AsyncDatabaseManager


@pytest.fixture(autouse=True)
async def setup_database(app: Application, tmp_path: Path) -> AsyncGenerator[None]:
    app.config["database"] = {
        "default": "sqlite",
        "connections": {
            "sqlite": {"driver": "sqlite", "database": tmp_path.joinpath("db.sqlite")}
        },
    }

    db = await app.container.get(AsyncDatabaseManager)

    async with db.connection("sqlite") as connection:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER NOT NULL,
                first_name VARCHAR NOT NULL,
                last_name VARCHAR,
                email VARCHAR NOT NULL,
                PRIMARY KEY (id)
            );
            """
        )

        await connection.commit()

    yield
