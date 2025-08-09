from typing import TYPE_CHECKING

from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.queue.asynchronous.connectors.database import AsyncDatabaseConnector
    from expanse.queue.asynchronous.queue_manager import AsyncQueueManager


class QueueServiceProvider(ServiceProvider):
    async def register(self) -> None:
        await self._register_queue_manager()

    async def _register_queue_manager(self) -> None:
        from expanse.queue.asynchronous.queue_manager import AsyncQueueManager

        self._container.singleton(AsyncQueueManager, self._create_queue_manager)

    async def _create_queue_manager(self) -> "AsyncQueueManager":
        from expanse.core.application import Application
        from expanse.queue.asynchronous.queue_manager import AsyncQueueManager

        manager = AsyncQueueManager(await self._container.get(Application))
        manager.add_connector("database", self._create_database_connector)

        return manager

    async def _create_database_connector(self) -> "AsyncDatabaseConnector":
        from expanse.database.asynchronous.database_manager import AsyncDatabaseManager
        from expanse.queue.asynchronous.connectors.database import (
            AsyncDatabaseConnector,
        )

        return AsyncDatabaseConnector(await self._container.get(AsyncDatabaseManager))
