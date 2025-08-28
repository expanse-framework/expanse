from typing import NotRequired
from typing import TypedDict

from expanse.container.container import Container
from expanse.queue.asynchronous.connectors.connector import AsyncConnector
from expanse.queue.asynchronous.queues.database_queue import AsyncDatabaseQueue


class Config(TypedDict):
    connection: str | None
    table: str
    queue: str
    retry_after: NotRequired[int]
    dispatch_after_commit: NotRequired[bool]


class AsyncDatabaseConnector(AsyncConnector):
    """
    Asynchronous database connector for Expanse.
    This class is used to connect to a database asynchronously.
    """

    def __init__(self, container: Container) -> None:
        self._container: Container = container

    async def connect(self, config: Config) -> AsyncDatabaseQueue:
        """
        Connect to the database asynchronously.
        """
        return AsyncDatabaseQueue(
            self._db,
            config["connection"],
            config["table"],
            config["queue"],
            retry_after=config.get("retry_after", 60),
            dispatch_after_commit=config.get("dispatch_after_commit", False),
        )
