from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from expanse.configuration.config import Config
from expanse.redis.asynchronous.redis_manager import RedisManager
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.redis.asynchronous.connections.connection import Connection


class RedisServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.redis.asynchronous.connections.connection import Connection
        from expanse.redis.asynchronous.redis_manager import RedisManager

        self._container.singleton(RedisManager, self._create_redis_manager)
        self._container.singleton(Connection, self._create_connection)

    async def _create_redis_manager(
        self, config: Config
    ) -> AsyncGenerator["RedisManager", None]:
        from expanse.redis.asynchronous.redis_manager import RedisManager

        manager = RedisManager(config)

        yield manager

        await manager.close()

    async def _create_connection(
        self, manager: RedisManager, name: str | None = None
    ) -> AsyncGenerator["Connection", None]:
        connection = await manager.connection(name)

        yield connection

        await connection.aclose()
