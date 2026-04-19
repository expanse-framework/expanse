from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Config(BaseSettings):
    # Default storage
    #
    # The default storage that should be used
    # when no storage is explicitly specified.
    storage: str = "local"

    # Storages
    #
    # The storages that are defined for your applications.
    # They can all be defined with environment variables in you `.env` file.
    # For instance:
    # >>> STORAGE_STORAGES__LOCAL__DRIVER=local
    storages: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "local": {"driver": "local", "root": "./storage"},
        }
    )

    model_config = SettingsConfigDict(env_prefix="storage_", env_nested_delimiter="__")
