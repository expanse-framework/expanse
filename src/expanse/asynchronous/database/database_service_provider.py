from collections.abc import AsyncGenerator

from expanse.asynchronous.database.connection import Connection
from expanse.asynchronous.database.database_manager import DatabaseManager
from expanse.asynchronous.database.database_manager import (
    DatabaseManager as DatabaseManagerContract,
)
from expanse.asynchronous.database.session import Session
from expanse.asynchronous.support.service_provider import ServiceProvider


class DatabaseServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(DatabaseManager)
        self._container.scoped(Session, self._create_session)
        self._container.scoped(Connection, self._create_connection)

    async def _create_connection(
        self,
        db: DatabaseManagerContract,
        name: str | None = None,
    ) -> AsyncGenerator[Connection]:
        connection = db.connection(name)

        await connection.start()

        yield connection

        await connection.close()

    async def _create_session(
        self,
        db: DatabaseManagerContract,
        name: str | None = None,
    ) -> AsyncGenerator[Session]:
        session = db.session(name)

        yield session

        await session.close()
