from typing import TYPE_CHECKING
from typing import Any

from sqlalchemy import URL
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.util import immutabledict

from expanse.core.application import Application
from expanse.database.config import MySQLConfig
from expanse.database.config import PostgreSQLConfig
from expanse.database.config import SQLiteConfig
from expanse.database.exceptions import UnconfiguredDatabaseDriverError
from expanse.database.exceptions import UnconfiguredDatabaseError
from expanse.database.exceptions import UnsupportedDatabaseDriverError
from expanse.database.session import AsyncSession


if TYPE_CHECKING:
    from collections.abc import Callable


class AsyncDatabaseManager:
    def __init__(self, app: Application) -> None:
        self._app: Application = app
        self._engines: dict[str, AsyncEngine] = {}
        self._factories: dict[str, async_sessionmaker] = {}
        self._creators: dict[
            str, Callable[[AsyncDatabaseManager, str, dict[str, Any]], AsyncEngine]
        ] = {}

    def connection(self, name: str | None = None) -> AsyncConnection:
        engine = self.configure_engine(name)

        connection = engine.connect()

        assert isinstance(connection, AsyncConnection)

        return connection

    def session(self, name: str | None = None) -> AsyncSession:
        name = name or self.get_default_connection()

        if name in self._factories:
            return self._factories[name]()

        engine = self.configure_engine(name)
        factory = async_sessionmaker(engine, class_=AsyncSession)

        self._factories[name] = factory

        return self._factories[name]()

    def create_base_engine(self, url: URL, **kwargs) -> AsyncEngine:
        sync_engine = create_engine(url, **kwargs)

        return AsyncEngine(sync_engine)

    def configure_engine(self, name: str | None = None) -> AsyncEngine:
        name = name or self.get_default_connection()

        if name in self._engines:
            return self._engines[name]

        config = self._configuration(name)

        self._engines[name] = self._create_engine(name, config)

        return self._engines[name]

    async def dispose(self) -> None:
        """
        Dispose of all database engines (and associated connection pools) and clear the engine and factory caches.
        """
        for engine in self._engines.values():
            await engine.dispose()

        self._engines.clear()
        self._factories.clear()

    def extend(
        self,
        driver: str,
        creator: "Callable[[AsyncDatabaseManager, str, dict[str, Any]], AsyncEngine]",
    ) -> None:
        """
        Extend the database manager with a custom driver and its corresponding engine creation logic.

        :param driver: The name of the custom database driver.
        :param creator: A callable that takes a connection name and its raw configuration, and returns an AsyncEngine instance.
        """
        self._creators[driver] = creator

    def _create_engine(self, name: str, raw_config: dict[str, Any]) -> AsyncEngine:
        driver = raw_config.get("driver")
        if driver is None:
            raise UnconfiguredDatabaseDriverError(
                f"The database connection [{name}] does not specify a driver."
            )

        match driver:
            case "sqlite":
                return self._create_sqlite_engine(name, raw_config)
            case "postgresql":
                return self._create_postgresql_engine(name, raw_config)
            case "mysql":
                return self._create_mysql_engine(name, raw_config)
            case _:
                if driver not in self._creators:
                    raise UnsupportedDatabaseDriverError(
                        f"The database connection [{name}] specifies an unsupported driver [{driver}]."
                    )

                return self._creators[driver](self, name, raw_config)

    def _create_sqlite_engine(
        self, name: str, raw_config: dict[str, Any]
    ) -> AsyncEngine:
        config = SQLiteConfig.model_validate(raw_config)

        if config.url is not None:
            url = make_url(str(config.url))
            if url.drivername == "sqlite":
                url = URL("sqlite+aiosqlite", *url[1:])
        else:
            if config.database is None:
                raise UnconfiguredDatabaseError(
                    f"The database connection [{name}] does not specify a database."
                )

            database_path = config.database

            database: str
            if database_path == ":memory:":
                database = database_path
            else:
                if not database_path.is_absolute():
                    database_path = self._app.base_path / database_path

                database_path.parent.mkdir(parents=True, exist_ok=True)

                database = database_path.as_posix()

            url = URL(
                drivername="sqlite+aiosqlite",
                database=database,
                host=None,
                port=None,
                username=None,
                password=None,
                query=immutabledict(),
            )

        engine = self.create_base_engine(url)

        if config.foreign_key_constraints:

            @event.listens_for(engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        return engine

    def _create_postgresql_engine(
        self, name: str, raw_config: dict[str, Any]
    ) -> AsyncEngine:
        config = PostgreSQLConfig.model_validate(raw_config)

        if config.url is not None:
            url = make_url(str(config.url))
            if url.drivername in {"postgresql", "postgresql+psycopg"}:
                url = URL("postgresql+psycopg_async", *url[1:])
        else:
            drivername: str = "postgresql"
            if config.dbapi is not None:
                dbapi = config.dbapi
                if dbapi == "psycopg":
                    dbapi = "psycopg_async"

                drivername += f"+{dbapi}"
            else:
                drivername += "+psycopg_async"

            query: dict[str, Any] = {}

            if config.sslmode is not None:
                query["sslmode"] = config.sslmode

            url = URL(
                drivername=drivername,
                host=config.host,
                port=config.port,
                database=config.database,
                username=config.username,
                password=config.password,
                query=immutabledict(query),
            )

        engine = self.create_base_engine(
            url, **config.pool.model_dump(exclude_none=True)
        )

        if config.search_path:

            @event.listens_for(engine.sync_engine, "connect", insert=True)
            def set_search_path(dbapi_connection, connection_record):
                existing_autocommit = dbapi_connection.autocommit
                dbapi_connection.autocommit = True
                cursor = dbapi_connection.cursor()
                cursor.execute(f"SET SESSION search_path='{config.search_path}'")
                cursor.close()
                dbapi_connection.autocommit = existing_autocommit

        return engine

    def _create_mysql_engine(
        self, name: str, raw_config: dict[str, Any]
    ) -> AsyncEngine:
        config = MySQLConfig.model_validate(raw_config)

        if config.url is not None:
            url = make_url(str(config.url))
            if url.drivername in {"mysql"}:
                url = URL("mysql+asyncmy", *url[1:])
        else:
            drivername: str = "mysql"
            if config.dbapi is not None:
                drivername += f"+{config.dbapi}"
            else:
                drivername += "+asyncmy"

            query: dict[str, Any] = {}

            if config.charset is not None:
                query["charset"] = config.charset

            url = URL(
                drivername=drivername,
                host=config.host,
                port=config.port,
                database=config.database,
                username=config.username,
                password=config.password,
                query=immutabledict(query),
            )

        engine = self.create_base_engine(
            url, **config.pool.model_dump(exclude_none=True)
        )

        return engine

    def get_default_connection(self) -> str:
        return self._app.config.get("database.default")

    def _configuration(self, name: str) -> Any:
        connections = self._app.config.get("database.connections", {})

        if name not in connections:
            raise UnconfiguredDatabaseError(
                f"The database connection [{name}] is not configured."
            )

        return connections[name]
