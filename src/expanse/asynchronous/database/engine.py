from sqlalchemy.ext.asyncio import AsyncEngine as BaseAsyncEngine

from expanse.asynchronous.database.connection import Connection


class Engine(BaseAsyncEngine):
    _connection_cls = Connection
