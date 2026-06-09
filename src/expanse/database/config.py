from pathlib import Path
from typing import Literal

from pydantic import AnyUrl
from pydantic import BaseModel
from pydantic import Field
from pydantic_settings import SettingsConfigDict


class PoolConfig(BaseModel):
    pre_ping: bool | None = None
    size: int | None = None
    timeout: float | None = None
    recycle: int | None = None
    max_overflow: int | None = None


class SQLiteConfig(PoolConfig, BaseModel):
    driver: Literal["sqlite"] = "sqlite"
    url: AnyUrl | None = None
    database: Path | Literal[":memory:"] | None = None
    foreign_key_constraints: bool = Field(default=True, alias="foreign_keys")
    pool: PoolConfig = PoolConfig()
    connect_args: dict = Field(default_factory=dict)

    model_config = SettingsConfigDict(arbitrary_types_allowed=True)


class MySQLConfig(BaseModel):
    driver: Literal["mysql"] = "mysql"
    dbapi: (
        Literal["mysql-connector-python", "mysqldb", "pymysql", "asyncmy", "aiomysql"]
        | None
    ) = None
    url: AnyUrl | None = None
    host: str | None = None
    port: int = 3306
    database: str | None = None
    username: str = ""
    password: str = ""
    charset: str = "utf8mb4"
    pool: PoolConfig = PoolConfig()


class PostgreSQLConfig(BaseModel):
    driver: Literal["postgresql"] = "postgresql"
    dbapi: (
        Literal["psycopg", "psycopg2", "pg8000", "psycopg_async", "asyncpg"] | None
    ) = None
    url: AnyUrl | None = None
    host: str | None = None
    port: int = 5432
    database: str | None = None
    username: str = ""
    password: str = ""
    search_path: str | None = None
    sslmode: Literal["prefer", "require"] | None = None
    pool: PoolConfig = PoolConfig()
