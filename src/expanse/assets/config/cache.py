from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Config(BaseSettings):
    # Default cache store
    #
    # The default cache store that should be used when no store is explicitly specified.
    # Use the `CACHE_STORE` environment variable to set this value in your `.env` file.
    # For instance:
    # >>> CACHE_STORE=database
    store: str = "memory"

    # Cache stores
    #
    # The cache stores that are defined for your applications.
    # They can all be defined with environment variables in you `.env` file.
    # For instance:
    # >>> CACHE_STORES__DATABASE__DRIVER=database
    # >>> CACHE_STORES__DATABASE__CONNECTION=default
    stores: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "memory": {"driver": "memory"},
        }
    )

    model_config = SettingsConfigDict(env_prefix="CACHE_", env_nested_delimiter="__")
