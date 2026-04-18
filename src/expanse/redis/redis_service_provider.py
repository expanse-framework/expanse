from collections.abc import AsyncGenerator
from collections.abc import Generator
from typing import TYPE_CHECKING

from expanse.configuration.config import Config
from expanse.redis.asynchronous.redis_manager import RedisManager as AsyncRedisManager
from expanse.redis.synchronous.redis_manager import RedisManager as SyncRedisManager
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.redis.asynchronous.connections.connection import (
        Connection as AsyncConnection,
    )
    from expanse.redis.synchronous.connections.connection import (
        Connection as SyncConnection,
    )


class RedisServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.redis.asynchronous.connections.connection import (
            Connection as AsyncConnection,
        )
        from expanse.redis.asynchronous.redis_manager import (
            RedisManager as AsyncRedisManager,
        )
        from expanse.redis.synchronous.connections.connection import (
            Connection as SyncConnection,
        )
        from expanse.redis.synchronous.redis_manager import (
            RedisManager as SyncRedisManager,
        )

        self._container.singleton(AsyncRedisManager, self._create_async_redis_manager)
        self._container.singleton(AsyncConnection, self._create_async_connection)
        self._container.singleton(SyncRedisManager, self._create_sync_redis_manager)
        self._container.singleton(SyncConnection, self._create_sync_connection)

    async def _create_async_redis_manager(
        self, config: Config
    ) -> AsyncGenerator["AsyncRedisManager", None]:
        from expanse.redis.asynchronous.redis_manager import RedisManager

        manager = RedisManager(config)

        yield manager

        await manager.close()

    async def _create_async_connection(
        self, manager: AsyncRedisManager, name: str | None = None
    ) -> AsyncGenerator["AsyncConnection", None]:
        connection = await manager.connection(name)

        yield connection

        await connection.aclose()

    def _create_sync_redis_manager(
        self, config: Config
    ) -> Generator["SyncRedisManager", None, None]:
        from expanse.redis.synchronous.redis_manager import RedisManager

        manager = RedisManager(config)

        yield manager

        manager.close()

    def _create_sync_connection(
        self, manager: SyncRedisManager, name: str | None = None
    ) -> Generator["SyncConnection", None, None]:
        connection = manager.connection(name)

        yield connection

        connection.close()
