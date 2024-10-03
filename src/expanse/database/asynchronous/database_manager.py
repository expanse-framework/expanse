from typing import Any

from sqlalchemy import URL
from sqlalchemy import event
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.util import immutabledict

from expanse.core.application import Application
from expanse.database._utils import create_engine
from expanse.database.config import DatabaseConfig
from expanse.database.config import MySQLConfig
from expanse.database.config import PostgreSQLConfig
from expanse.database.config import SQLiteConfig
from expanse.database.connection import AsyncConnection
from expanse.database.engine import AsyncEngine
from expanse.database.session import AsyncSession


class AsyncDatabaseManager:
    def __init__(self, app: Application) -> None:
        self._app: Application = app
        self._engines: dict[str, AsyncEngine] = {}
        self._factories: dict[str, async_sessionmaker] = {}

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

        if not config:
            raise

        self._engines[name] = self._create_engine(config)

        return self._engines[name]

    def _create_engine(self, raw_config: dict[str, Any]) -> AsyncEngine:
        config = DatabaseConfig.model_validate(raw_config).root

        match config:
            case SQLiteConfig():
                return self._create_sqlite_engine(config)

            case PostgreSQLConfig():
                return self._create_postgresql_engine(config)

            case MySQLConfig():
                return self._create_mysql_engine(config)

    def _create_sqlite_engine(self, config: SQLiteConfig) -> AsyncEngine:
        if config.url is not None:
            url = make_url(str(config.url))
            if url.drivername == "sqlite":
                url = URL("sqlite+aiosqlite", *url[1:])
        else:
            if config.database is None:
                raise ValueError("The SQLite database path is not configured.")

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

    def _create_postgresql_engine(self, config: PostgreSQLConfig) -> AsyncEngine:
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

    def _create_mysql_engine(self, config: MySQLConfig) -> AsyncEngine:
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
            raise ValueError(f"The database connection [{name}] not configured.")

        return connections[name]
