from pathlib import Path
from typing import TYPE_CHECKING

from expanse.container.container import Container
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.core.console.portal import Portal
    from expanse.queue.asynchronous.connectors.database import AsyncDatabaseConnector
    from expanse.queue.asynchronous.queue_manager import AsyncQueueManager
    from expanse.queue.asynchronous.queues.queue import AsyncQueue


class QueueServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.queue.asynchronous.queues.queue import AsyncQueue

        await self._register_queue_manager()
        self._container.scoped(AsyncQueue, self._create_queue)

    async def boot(self) -> None:
        from expanse.core.console.portal import Portal

        await self._container.on_resolved(Portal, self._register_command_path)

    async def _register_queue_manager(self) -> None:
        from expanse.queue.asynchronous.queue_manager import AsyncQueueManager

        self._container.scoped(AsyncQueueManager, self._create_queue_manager)

    async def _create_queue_manager(self, container: Container) -> "AsyncQueueManager":
        from expanse.queue.asynchronous.queue_manager import AsyncQueueManager
        from expanse.queue.asynchronous.registry import AsyncQueueConnectorRegistry

        registry = AsyncQueueConnectorRegistry()
        registry.add_connector("database", self._create_database_connector)

        manager = AsyncQueueManager(container, registry)

        return manager

    async def _create_queue(
        self, manager: "AsyncQueueManager", name: str | None = None
    ) -> "AsyncQueue":
        return await manager.queue(name)

    async def _create_database_connector(self) -> "AsyncDatabaseConnector":
        from expanse.database.asynchronous.database_manager import AsyncDatabaseManager
        from expanse.queue.asynchronous.connectors.database import (
            AsyncDatabaseConnector,
        )

        return AsyncDatabaseConnector(await self._container.get(AsyncDatabaseManager))

    async def _register_command_path(self, portal: "Portal") -> None:
        await portal.load_path(Path(__file__).parent.joinpath("console/commands"))
