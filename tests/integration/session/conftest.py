import os

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from expanse.core.application import Application
from expanse.database.asynchronous.database_manager import AsyncDatabaseManager
from expanse.testing.command_tester import CommandTester


if TYPE_CHECKING:
    from expanse.configuration.config import Config


@pytest.fixture(autouse=True)
async def setup_databases(
    app: Application, tmp_path: Path, command_tester: CommandTester
) -> AsyncGenerator[None]:
    config: Config = app.config

    app.config["paths"]["database"] = (
        Path(__file__).parent.joinpath("fixtures").relative_to(app.base_path)
    )

    config["database"] = {
        "default": "sqlite",
        "connections": {
            "sqlite": {"driver": "sqlite", "database": tmp_path.joinpath("db.sqlite")},
            "postgresql": {
                "driver": "postgresql",
                "url": f"postgresql://postgres:password@127.0.0.1:{os.getenv('POSTGRES_TEST_PORT', 5432)}/expanse",
            },
            "mysql": {
                "driver": "mysql",
                "url": f"mysql://root:password@127.0.0.1:{os.getenv('MYSQL_TEST_PORT', 3306)}/expanse",
            },
        },
    }

    db = await app.container.get(AsyncDatabaseManager)

    for connection in config["database"]["connections"]:
        async with db.connection(connection) as connection:
            await connection.execute("DROP TABLE IF EXISTS sessions")
            await connection.execute("DROP TABLE IF EXISTS alembic_version")
            await connection.commit()

    yield

    for connection in config["database"]["connections"]:
        async with db.connection(connection) as connection:
            await connection.execute("DROP TABLE IF EXISTS sessions")
            await connection.execute("DROP TABLE IF EXISTS alembic_version")
            await connection.commit()
