from collections.abc import Awaitable
from collections.abc import Callable
from typing import Annotated

from expanse.asynchronous.container.container import Container
from expanse.asynchronous.contracts.database.connection import Connection
from expanse.asynchronous.contracts.database.database_manager import (
    DatabaseManager as DatabaseManagerContract,
)
from expanse.asynchronous.contracts.database.session import Session
from expanse.asynchronous.database.database_manager import DatabaseManager
from expanse.asynchronous.support.service_provider import ServiceProvider


class DatabaseServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._app.singleton(DatabaseManagerContract, DatabaseManager)
        self._app.scoped(Session, self._create_session)
        self._app.scoped(Connection, self._create_connection)

    async def _create_connection(
        self,
        container: Container,
        db: DatabaseManagerContract,
        name: str | None = None,
    ) -> Connection:
        session = db.connection(name)

        container.terminating(self._close_connection(name))

        await session.start()

        return session

    async def _create_session(
        self,
        container: Container,
        db: DatabaseManagerContract,
        name: str | None = None,
    ) -> Session:
        session = db.session(name)

        container.terminating(self._close_session(name))

        return session

    def _close_session(self, name: str | None) -> Callable[[Session], Awaitable[None]]:
        if name is not None:

            async def close(session: Annotated[Session, name]) -> None:
                await session.close()

        else:

            async def close(session: Session) -> None:
                await session.close()

        return close

    def _close_connection(
        self, name: str | None
    ) -> Callable[[Connection], Awaitable[None]]:
        if name is not None:

            async def close(connection: Annotated[Connection, name]) -> None:
                await connection.close()

        else:

            async def close(connection: Connection) -> None:
                await connection.close()

        return close
