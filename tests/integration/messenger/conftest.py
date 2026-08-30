from __future__ import annotations

import os

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from sqlalchemy import text

from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.database.database_manager import DatabaseManager
from expanse.messenger.serializers.serializer import Serializer
from expanse.serialization.serialization_manager import SerializationManager
from expanse.serialization.serializers.dataclass import DataclassSerializer


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from expanse.configuration.config import Config
    from expanse.core.application import Application
    from expanse.testing.command_tester import CommandTester


@pytest.fixture()
def serializer() -> SerializerContract:
    serialization_manager = SerializationManager()
    serialization_manager.register_serializer(DataclassSerializer())

    return Serializer(serialization_manager)


@pytest.fixture(autouse=True)
def configure_messenger(app: Application, serializer: Serializer) -> None:
    serialization_manager = SerializationManager()
    serialization_manager.register_serializer(DataclassSerializer())
    app.container.instance(SerializerContract, serializer)


@pytest.fixture()
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
                "url": f"postgresql://postgres:password@127.0.0.1:{os.getenv('POSTGRES_TEST_PORT', '5432')}/expanse",
            },
            "mysql": {
                "driver": "mysql",
                "url": f"mysql://root:password@127.0.0.1:{os.getenv('MYSQL_TEST_PORT', '3306')}/expanse",
            },
        },
    }

    db = await app.container.get(DatabaseManager)

    for connection_name in config["database"]["connections"]:
        with db.connection(connection_name) as connection:
            connection.execute(text("DROP TABLE IF EXISTS messages"))
            connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
            connection.commit()

    yield

    for connection_name in config["database"]["connections"]:
        with db.connection(connection_name) as connection:
            connection.execute(text("DROP TABLE IF EXISTS messages"))
            connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
            connection.commit()
