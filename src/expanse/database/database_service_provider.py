from collections.abc import Generator

from expanse.contracts.database.connection import Connection
from expanse.contracts.database.database_manager import (
    DatabaseManager as DatabaseManagerContract,
)
from expanse.contracts.database.session import Session
from expanse.database.database_manager import DatabaseManager
from expanse.support.service_provider import ServiceProvider


class DatabaseServiceProvider(ServiceProvider):
    def register(self) -> None:
        self._container.singleton(DatabaseManagerContract, DatabaseManager)
        self._container.scoped(Session, self._create_session)
        self._container.scoped(Connection, self._create_connection)

    def _create_connection(
        self, db: DatabaseManagerContract, name: str | None = None
    ) -> Generator[Connection]:
        connection = db.connection(name)

        yield connection

        connection.close()

    def _create_session(
        self, db: DatabaseManagerContract, name: str | None = None
    ) -> Generator[Session]:
        session = db.session(name)

        yield session

        session.close()
