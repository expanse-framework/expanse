from sqlalchemy.ext.asyncio import AsyncEngine as BaseAsyncEngine

from expanse.database.connection import AsyncConnection


class AsyncEngine(BaseAsyncEngine):
    _connection_cls = AsyncConnection
