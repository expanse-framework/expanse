from sqlalchemy.ext.asyncio import AsyncEngine as BaseAsyncEngine

from expanse.database.asynchronous.connection import AsyncConnection


class AsyncEngine(BaseAsyncEngine):
    _connection_cls = AsyncConnection
