from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from expanse.database.config import DatabaseConfig
from expanse.database.config import SQLiteConfig


class Config(BaseSettings):
    default: str = Field(validation_alias="db_connection", default="sqlite")

    connections: dict[str, DatabaseConfig] = Field(
        default={"sqlite": SQLiteConfig(database=Path("database/database.sqlite"))}
    )

    model_config = SettingsConfigDict(
        env_prefix="DB_", env_nested_delimiter="__", arbitrary_types_allowed=True
    )
