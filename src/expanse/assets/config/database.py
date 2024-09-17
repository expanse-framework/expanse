from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from expanse.database.config import DatabaseConfig
from expanse.database.config import SQLiteConfig


class Config(BaseSettings):
    # Default database connection
    #
    # The default database connection that should be used
    # when no connection is explicitly specified.
    default: str = Field(validation_alias="db_connection", default="sqlite")

    # Database connections
    #
    # The database connections that are defined for your applications.
    # They can all be defined with environment variables in you `.env` file.
    # For instance:
    # >>> DB_CONNECTIONS__SQLITE__DRIVER=sqlite
    # >>> DB_CONNECTIONS__SQLITE__DATABASE=database/database.sqlite
    connections: dict[str, DatabaseConfig] = Field(
        default={"sqlite": SQLiteConfig(database=Path("database/database.sqlite"))}
    )

    model_config = SettingsConfigDict(env_prefix="DB_", env_nested_delimiter="__")
