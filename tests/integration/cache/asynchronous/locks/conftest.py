from __future__ import annotations

import os

from typing import TYPE_CHECKING

import pytest

from expanse.redis.asynchronous.redis_manager import RedisManager


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from expanse.core.application import Application
    from expanse.redis.asynchronous.connections.connection import Connection


@pytest.fixture(autouse=True)
async def setup_redis(app: Application) -> AsyncGenerator[None]:
    from expanse.redis.redis_service_provider import RedisServiceProvider

    app.config["redis"] = {
        "connection": "default",
        "connections": {
            "default": {
                "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/1"
            }
        },
    }

    await RedisServiceProvider(app.container).register()

    yield

    manager = await app.container.get(RedisManager)
    connection = await manager.connection("default")
    await connection.flushdb()


@pytest.fixture()
async def connection(app: Application) -> Connection:
    manager = await app.container.get(RedisManager)

    return await manager.connection("default")
