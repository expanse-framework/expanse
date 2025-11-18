from collections.abc import AsyncGenerator
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

from expanse.configuration.config import Config
from expanse.core.application import Application
from expanse.database.connection import AsyncConnection
from expanse.database.connection import Connection
from expanse.database.database_manager import AsyncDatabaseManager
from expanse.database.database_manager import DatabaseManager
from expanse.database.migration.migrator import Migrator
from expanse.database.session import AsyncSession
from expanse.database.session import Session
from expanse.exceptions.handler import ExceptionHandler
from expanse.pagination.pagination_manager import PaginationManager
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.core.console.portal import Portal


class DatabaseServiceProvider(ServiceProvider):
    async def register(self) -> None:
        await self._register_async()
        await self._register_sync()

        self._container.singleton(Migrator, self._create_migrator)

        await self._container.on_resolved(
            ExceptionHandler, self._configure_exception_handler
        )

    async def boot(self) -> None:
        from expanse.core.console.portal import Portal

        await self._container.on_resolved(Portal, self._register_command_path)

    async def _register_async(self) -> None:
        self._container.singleton(AsyncDatabaseManager)
        self._container.scoped(AsyncSession, self._create_async_session)
        self._container.scoped(AsyncConnection, self._create_async_connection)

    async def _register_sync(self) -> None:
        self._container.singleton(DatabaseManager)
        self._container.scoped(Session, self._create_session)
        self._container.scoped(Connection, self._create_connection)

    async def _create_async_connection(
        self, db: AsyncDatabaseManager, name: str | None = None
    ) -> AsyncGenerator[AsyncConnection]:
        connection = db.connection(name)

        await connection.start()

        yield connection

        await connection.close()

    async def _create_async_session(
        self,
        db: AsyncDatabaseManager,
        pagination_manager: PaginationManager,
        name: str | None = None,
    ) -> AsyncGenerator[AsyncSession]:
        session = db.session(name).set_pagination_manager(pagination_manager)

        yield session

        await session.close()

    def _create_connection(
        self, db: DatabaseManager, name: str | None = None
    ) -> Generator[Connection]:
        connection = db.connection(name)

        yield connection

        connection.close()

    def _create_session(
        self,
        db: DatabaseManager,
        pagination_manager: PaginationManager,
        name: str | None = None,
    ) -> Generator[Session]:
        session = db.session(name).set_pagination_manager(pagination_manager)

        yield session

        session.close()

    async def _register_command_path(self, portal: "Portal") -> None:
        await portal.load_path(Path(__file__).parent.joinpath("console/commands"))

    async def _create_migrator(self, app: Application, config: Config) -> Migrator:
        from expanse.database.orm.model import Model

        migrator = Migrator(app)
        migrator.config.attributes["db"] = await self._container.get(DatabaseManager)
        migrator.config.attributes["include_name"] = migrator.include_name
        migrator.config.attributes["target_metadata"] = Model.metadata

        return migrator

    async def _configure_exception_handler(self, handler: ExceptionHandler) -> None:
        from sqlalchemy.exc import NoResultFound

        from expanse.core.http.exceptions import HTTPException

        def _no_result_found_handler(e: NoResultFound) -> HTTPException:
            return HTTPException(404, str(e))

        # NoResultFound exceptions should be ignored since they will automatically
        # be converted to 404 responses.
        handler.ignore(NoResultFound)
        handler.prepare_using(NoResultFound, _no_result_found_handler)
