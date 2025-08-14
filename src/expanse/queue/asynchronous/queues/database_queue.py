import json

from typing import NamedTuple

import pendulum

from sqlalchemy import TableClause

from expanse.database.asynchronous.connection import AsyncConnection
from expanse.queue.asynchronous.queues.queue import AsyncQueue
from expanse.queue.models.job import Job
from expanse.types.queue.job import JobType


class JobRow(NamedTuple):
    id: int


class AsyncDatabaseQueue(AsyncQueue):
    """
    An asynchronous queue that uses a database for storage.
    This class is intended to be used with an asynchronous database driver.
    """

    def __init__(
        self,
        connection: AsyncConnection,
        table_name: str,
        queue: str = "default",
        retry_after: int = 60,
        dispatch_after_commit: bool = False,
    ) -> None:
        self._connection: AsyncConnection = connection
        self._table: TableClause = Job.__table__
        self._queue: str = queue
        self._retry_after: int = retry_after
        self._dispatch_after_commit: bool = dispatch_after_commit

    async def put(self, job: JobType, data: str = "", queue: str | None = None) -> None:
        await self._put_using(
            job,
            await self._create_payload(job, queue or self._queue, data),
            queue or self._queue,
            self._insert,
        )

    async def _insert(
        self, payload: dict[str, str | tuple[str, str]], queue: str | None
    ) -> int:
        query = self._table.insert().values(
            queue=queue or self._queue,
            created_at=pendulum.now(),
            payload=json.dumps(payload),
            attempts=0,
            reserved_at=None,
            available_at=pendulum.now(),
        )

        is_mysql = self._connection.engine.name == "mysql"

        if not is_mysql:
            query = query.returning(self._table.c.id)

        async with self._connection as connection:
            query
            result = await connection.execute(query)

            if is_mysql:
                return result.lastrowid

            return result.fetchone()[0]
