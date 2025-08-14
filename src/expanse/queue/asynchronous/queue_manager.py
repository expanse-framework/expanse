from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any

from expanse.core.application import Application
from expanse.queue.asynchronous.connectors.connector import AsyncConnector
from expanse.queue.asynchronous.queues.queue import AsyncQueue


class AsyncQueueManager:
    def __init__(self, app: Application) -> None:
        self._app: Application = app
        self._connectors: dict[str, Callable[[], Awaitable[AsyncConnector]]] = {}
        self._queues: dict[str, AsyncQueue] = {}

    async def queue(self, name: str | None = None) -> AsyncQueue:
        name = name or self.get_default_queue()

        return await self._resolve(name)

    def add_connector(
        self, name: str, connector: Callable[[], Awaitable[AsyncConnector]]
    ) -> None:
        self._connectors[name] = connector

    async def _resolve(self, name: str) -> AsyncQueue:
        config = self._configuration(name)

        driver: str = config["driver"]
        if driver not in self._connectors:
            raise ValueError(f"The queue driver [{driver}] is not configured.")

        connector = await self._connectors[driver]()

        return await connector.connect(config)

    def get_default_queue(self) -> str:
        return self._app.config.get("queue.default")

    def _configuration(self, name: str) -> dict[str, Any]:
        connections: dict[str, dict[str, Any]] = self._app.config.get(
            "queue.connections", {}
        )

        if name not in connections:
            raise ValueError(f"The database connection [{name}] not configured.")

        return connections[name]
