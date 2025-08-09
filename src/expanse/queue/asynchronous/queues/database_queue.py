from expanse.database.asynchronous.connection import AsyncConnection
from expanse.queue.asynchronous.queues.queue import AsyncQueue


class AsyncDatabaseQueue(AsyncQueue):
    """
    An asynchronous queue that uses a database for storage.
    This class is intended to be used with an asynchronous database driver.
    """

    def __init__(
        self,
        connection: AsyncConnection,
        table: str,
        queue: str = "default",
        retry_after: int = 60,
        dispatch_after_commit: bool = False,
    ) -> None:
        self._connection: AsyncConnection = connection
        self._table: str = table
        self._queue: str = queue
        self._retry_after: int = retry_after
        self._dispatch_after_commit: bool = dispatch_after_commit
