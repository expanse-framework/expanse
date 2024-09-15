from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING

from expanse.asynchronous.core.application import Application
from expanse.asynchronous.database.connection import Connection
from expanse.asynchronous.database.database_manager import DatabaseManager
from expanse.asynchronous.database.session import Session
from expanse.asynchronous.exceptions.handler import ExceptionHandler
from expanse.asynchronous.support.service_provider import ServiceProvider
from expanse.common.configuration.config import Config
from expanse.common.database.migration.migrator import Migrator


if TYPE_CHECKING:
    from expanse.asynchronous.core.console.gateway import Gateway


class DatabaseServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(DatabaseManager)
        self._container.scoped(Session, self._create_session)
        self._container.scoped(Connection, self._create_connection)
        self._container.singleton(Migrator, self._create_migrator)
        await self._container.on_resolved(
            ExceptionHandler, self._configure_exception_handler
        )

    async def boot(self) -> None:
        from expanse.asynchronous.core.console.gateway import Gateway

        await self._container.on_resolved(Gateway, self._register_command_path)

    async def _create_connection(
        self, db: DatabaseManager, name: str | None = None
    ) -> AsyncGenerator[Connection]:
        connection = db.connection(name)

        await connection.start()

        yield connection

        await connection.close()

    async def _create_session(
        self, db: DatabaseManager, name: str | None = None
    ) -> AsyncGenerator[Session]:
        session = db.session(name)

        yield session

        await session.close()

    async def _register_command_path(self, gateway: "Gateway") -> None:
        await gateway.load_path(Path(__file__).parent.joinpath("console/commands"))

    async def _create_migrator(self, app: Application, config: Config) -> Migrator:
        migrator = Migrator(app)

        # We want to build a synchronous database manager that can be safely
        # used in migrations and in env.py Alembic file.
        from expanse.core.application import Application as SyncApplication
        from expanse.database.database_manager import (
            DatabaseManager as SyncDatabaseManager,
        )

        sync_app = SyncApplication(app.base_path)
        sync_app.set_config(config)

        migrator.config.attributes["db"] = SyncDatabaseManager(sync_app)

        return migrator

    async def _configure_exception_handler(self, handler: ExceptionHandler) -> None:
        from sqlalchemy.exc import NoResultFound

        from expanse.common.core.http.exceptions import HTTPException

        def _no_result_found_handler(e: NoResultFound) -> HTTPException:
            return HTTPException(404, str(e))

        # NoResultFound exceptions should be ignored since they will automatically
        # be converted to 404 responses.
        handler.ignore(NoResultFound)
        handler.prepare_using(NoResultFound, _no_result_found_handler)
