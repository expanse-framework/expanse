from collections.abc import Callable
from typing import Annotated

from expanse.container.container import Container
from expanse.contracts.database.connection import Connection
from expanse.contracts.database.database_manager import (
    DatabaseManager as DatabaseManagerContract,
)
from expanse.contracts.database.session import Session
from expanse.database.database_manager import DatabaseManager
from expanse.support.service_provider import ServiceProvider


class DatabaseServiceProvider(ServiceProvider):
    def register(self) -> None:
        self._app.singleton(DatabaseManagerContract, DatabaseManager)
        self._app.scoped(Session, self._create_session)
        self._app.scoped(Connection, self._create_connection)

    def _create_connection(
        self, container: Container, db: DatabaseManagerContract, name: str | None = None
    ) -> Connection:
        session = db.connection(name)

        container.terminating(self._close_connection(name))

        return session

    def _create_session(
        self, container: Container, db: DatabaseManagerContract, name: str | None = None
    ) -> Session:
        session = db.session(name)

        container.terminating(self._close_session(name))

        return session

    def _close_session(self, name: str | None) -> Callable[[Session], None]:
        if name is not None:

            def close(session: Annotated[Session, name]) -> None:
                session.close()

        else:

            def close(session: Session) -> None:
                session.close()

        return close

    def _close_connection(self, name: str | None) -> Callable[[Connection], None]:
        if name is not None:

            def close(connection: Annotated[Connection, name]) -> None:
                connection.close()

        else:

            def close(connection: Connection) -> None:
                connection.close()

        return close
