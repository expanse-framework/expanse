import os

from collections.abc import AsyncGenerator

import pytest

from expanse.configuration.config import Config
from expanse.redis.asynchronous.redis_manager import RedisManager


pytestmark = pytest.mark.redis


@pytest.fixture(autouse=True)
async def setup_redis() -> AsyncGenerator[None]:

    yield

    # Clean up any leftover state from a previous run
    manager = RedisManager(
        Config(
            {
                "redis": {
                    "connection": "connection-0",
                    "connections": {
                        f"connection-{i}": {
                            "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/{i}"
                        }
                        for i in range(16)
                    },
                }
            }
        )
    )

    for i in range(16):
        connection = await manager.connection(f"connection-{i}")
        await connection.flushdb()
