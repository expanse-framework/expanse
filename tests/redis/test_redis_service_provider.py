from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.redis.asynchronous.connections.connection import Connection
from expanse.redis.asynchronous.redis_manager import RedisManager
from expanse.redis.redis_service_provider import RedisServiceProvider


if TYPE_CHECKING:
    from expanse.core.application import Application


async def test_service_provider_registers_redis_manager_and_connection(
    app: Application,
) -> None:
    provider = RedisServiceProvider(app.container)

    await provider.register()

    assert app.container.has(RedisManager)
    assert app.container.has(Connection)
