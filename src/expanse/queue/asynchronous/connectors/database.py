from typing import NotRequired
from typing import TypedDict

from expanse.database.asynchronous.connection import AsyncConnection
from expanse.database.asynchronous.database_manager import AsyncDatabaseManager
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

    _connection: AsyncConnection

    def __init__(self, db: AsyncDatabaseManager) -> None:
        self._db: AsyncDatabaseManager = db

    async def connect(self, config: Config) -> AsyncDatabaseQueue:
        """
        Connect to the database asynchronously.
        """
        self._connection = await self._db.connection(config["connection"])

        return AsyncDatabaseQueue(
            self._connection,
            config["table"],
            config["queue"],
            retry_after=config.get("retry_after", 60),
            dispatch_after_commit=config.get("dispatch_after_commit", False),
        )

    async def disconnect(self) -> None:
        """
        Disconnect from the database asynchronously.
        """
        if hasattr(self, "_connection"):
            await self._connection.close()
