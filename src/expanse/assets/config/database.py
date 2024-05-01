from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from expanse.common.foundation.helpers import database_path
from expanse.database.config import DatabaseConfig
from expanse.database.config import SQLiteConfig


class Config(BaseSettings):
    default: str = Field(validation_alias="db_connection", default="sqlite")

    connections: dict[str, DatabaseConfig] = {  # noqa: RUF012
        "sqlite": SQLiteConfig(database=database_path("database.sqlite"))
    }

    model_config = SettingsConfigDict(
        env_prefix="DB_", env_nested_delimiter="__", arbitrary_types_allowed=True
    )