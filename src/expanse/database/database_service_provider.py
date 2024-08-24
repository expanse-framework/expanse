from collections.abc import Generator

from expanse.database.connection import Connection
from expanse.database.database_manager import DatabaseManager
from expanse.database.session import Session
from expanse.support.service_provider import ServiceProvider


class DatabaseServiceProvider(ServiceProvider):
    def register(self) -> None:
        self._container.singleton(DatabaseManager)
        self._container.scoped(Session, self._create_session)
        self._container.scoped(Connection, self._create_connection)

    def _create_connection(
        self, db: DatabaseManager, name: str | None = None
    ) -> Generator[Connection]:
        connection = db.connection(name)

        yield connection

        connection.close()

    def _create_session(
        self, db: DatabaseManager, name: str | None = None
    ) -> Generator[Session]:
        session = db.session(name)

        yield session

        session.close()
