from collections.abc import Awaitable
from collections.abc import Callable

from expanse.queue.asynchronous.connectors.connector import AsyncConnector


class AsyncQueueConnectorRegistry:
    def __init__(self):
        self._connectors: dict[str, Callable[[], Awaitable[AsyncConnector]]] = {}

    def add_connector(
        self, name: str, connector: Callable[[], Awaitable[AsyncConnector]]
    ) -> None:
        self._connectors[name] = connector

    def connector(self, name: str) -> Callable[[], Awaitable[AsyncConnector]]:
        return self._connectors[name]

    def has(self, name: str) -> bool:
        return name in self._connectors
