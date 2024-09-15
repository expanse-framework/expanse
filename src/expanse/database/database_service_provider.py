from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

from expanse.common.database.migration.migrator import Migrator
from expanse.contracts.debug.exception_handler import ExceptionHandler
from expanse.core.application import Application
from expanse.database.connection import Connection
from expanse.database.database_manager import DatabaseManager
from expanse.database.session import Session
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.core.console.gateway import Gateway


class DatabaseServiceProvider(ServiceProvider):
    def register(self) -> None:
        self._container.singleton(DatabaseManager)
        self._container.scoped(Session, self._create_session)
        self._container.scoped(Connection, self._create_connection)
        self._container.singleton(Migrator, self._create_migrator)
        self._container.on_resolved(ExceptionHandler, self._configure_exception_handler)

    def boot(self) -> None:
        from expanse.core.console.gateway import Gateway

        self._container.on_resolved(Gateway, self._register_command_path)

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

    def _register_command_path(self, gateway: "Gateway") -> None:
        gateway.load_path(Path(__file__).parent.joinpath("console/commands"))

    def _create_migrator(self, app: Application, db: DatabaseManager) -> Migrator:
        migrator = Migrator(app)

        migrator.config.attributes["db"] = db

        return migrator

    def _configure_exception_handler(self, handler: ExceptionHandler) -> None:
        from sqlalchemy.exc import NoResultFound

        from expanse.common.core.http.exceptions import HTTPException

        def _no_result_found_handler(e: NoResultFound) -> HTTPException:
            return HTTPException(404, str(e))

        # NoResultFound exceptions should be ignored since they will automatically
        # be converted to 404 responses.
        handler.ignore(NoResultFound)
        handler.prepare_using(NoResultFound, _no_result_found_handler)
