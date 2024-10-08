from typing import Any

from sqlalchemy import URL
from sqlalchemy import event
from sqlalchemy import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.util import immutabledict

from expanse.core.application import Application
from expanse.database._utils import create_engine
from expanse.database.config import DatabaseConfig
from expanse.database.config import MySQLConfig
from expanse.database.config import PostgreSQLConfig
from expanse.database.config import SQLiteConfig
from expanse.database.synchronous.connection import Connection
from expanse.database.synchronous.engine import Engine
from expanse.database.synchronous.session import Session


class DatabaseManager:
    def __init__(self, app: Application) -> None:
        self._app: Application = app
        self._engines: dict[str, Engine] = {}
        self._factories: dict[str, sessionmaker] = {}

    def connection(self, name: str | None = None) -> Connection:
        engine = self.configure_engine(name)

        connection = engine.connect()

        return connection

    def session(self, name: str | None = None) -> Session:
        name = name or self.get_default_connection()

        if name in self._factories:
            return self._factories[name]()

        engine = self.configure_engine(name)
        factory = sessionmaker(engine, class_=Session)

        self._factories[name] = factory

        return self._factories[name]()

    def create_base_engine(self, url: URL, **kwargs) -> Engine:
        engine = create_engine(url, engine_class=Engine, **kwargs)

        return engine

    def configure_engine(self, name: str | None = None) -> Engine:
        name = name or self.get_default_connection()

        if name in self._engines:
            return self._engines[name]

        config = self._configuration(name)

        if not config:
            raise

        self._engines[name] = self._create_engine(config)

        return self._engines[name]

    def _create_engine(self, raw_config: dict[str, Any]) -> Engine:
        config = DatabaseConfig.model_validate(raw_config).root

        match config:
            case SQLiteConfig():
                return self._create_sqlite_engine(config)

            case PostgreSQLConfig():
                return self._create_postgresql_engine(config)

            case MySQLConfig():
                return self._create_mysql_engine(config)

    def _create_sqlite_engine(self, config: SQLiteConfig) -> Engine:
        if config.url is not None:
            url = make_url(str(config.url))
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
                drivername="sqlite",
                database=database,
                host=None,
                port=None,
                username=None,
                password=None,
                query=immutabledict(),
            )

        engine = self.create_base_engine(url)

        if config.foreign_key_constraints:

            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        return engine

    def _create_postgresql_engine(self, config: PostgreSQLConfig) -> Engine:
        if config.url is not None:
            url = make_url(str(config.url))
        else:
            drivername: str = "postgresql"
            if config.dbapi is not None:
                drivername += f"+{config.dbapi}"

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

            @event.listens_for(engine, "connect", insert=True)
            def set_search_path(dbapi_connection, connection_record):
                existing_autocommit = dbapi_connection.autocommit
                dbapi_connection.autocommit = True
                cursor = dbapi_connection.cursor()
                cursor.execute(f"SET SESSION search_path='{config.search_path}'")
                cursor.close()
                dbapi_connection.autocommit = existing_autocommit

        return engine

    def _create_mysql_engine(self, config: MySQLConfig) -> Engine:
        if config.url is not None:
            url = make_url(str(config.url))
        else:
            drivername: str = "mysql"
            if config.dbapi is not None:
                drivername += f"+{config.dbapi}"

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
