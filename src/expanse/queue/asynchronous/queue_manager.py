from typing import Any

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.queue.asynchronous.connectors.connector import AsyncConnector
from expanse.queue.asynchronous.queues.queue import AsyncQueue
from expanse.queue.asynchronous.registry import AsyncQueueConnectorRegistry


class AsyncQueueManager:
    def __init__(
        self, container: Container, registry: AsyncQueueConnectorRegistry
    ) -> None:
        self._container: Container = container
        self._registry: AsyncQueueConnectorRegistry = registry
        self._queues: dict[str, AsyncQueue] = {}
        self._connectors: dict[str, AsyncConnector] = {}

    async def queue(self, name: str | None = None) -> AsyncQueue:
        name = name or await self.get_default_queue()

        if name in self._queues:
            return self._queues[name]

        queue = await self._resolve(name)

        self._queues[name] = queue

        return queue

    async def terminate(self) -> None:
        for connector in self._connectors.values():
            await connector.disconnect()

    async def _resolve(self, name: str) -> AsyncQueue:
        config = await self._configuration(name)

        driver: str = config["driver"]
        if not self._registry.has(driver):
            raise ValueError(f"The queue driver [{driver}] is not configured.")

        connector: AsyncConnector = await self._container.call(
            self._registry.connector(driver)
        )

        queue = await connector.connect(config)

        self._connectors[name] = connector

        return queue

    async def get_default_queue(self) -> str:
        config = await self._container.get(Config)

        return config.get("queue.default")

    async def _configuration(self, name: str) -> dict[str, Any]:
        config = await self._container.get(Config)

        connections: dict[str, dict[str, Any]] = config.get("queue.connections", {})

        if name not in connections:
            raise ValueError(f"The database connection [{name}] not configured.")

        return connections[name]
