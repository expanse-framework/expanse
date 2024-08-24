from pathlib import Path
from typing import Annotated
from typing import Literal

from pydantic import AnyUrl
from pydantic import BaseModel
from pydantic import Field
from pydantic import RootModel
from pydantic_settings import SettingsConfigDict


class PoolConfig(BaseModel):
    pool_pre_ping: bool | None = None
    pool_size: int | None = None
    pool_timeout: float | None = None
    pool_recycle: int | None = None
    max_overflow: int | None = None


class SQLiteConfig(PoolConfig, BaseModel):
    driver: Literal["sqlite"] = "sqlite"
    url: AnyUrl | None = None
    database: Path | Literal[":memory:"] | None = None
    foreign_key_constraints: bool = Field(default=True, alias="foreign_keys")

    model_config = SettingsConfigDict(arbitrary_types_allowed=True)


class PostgreSQLConfig(PoolConfig, BaseModel):
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


class DatabaseConfig(RootModel):
    root: Annotated[SQLiteConfig | PostgreSQLConfig, Field(discriminator="driver")]
