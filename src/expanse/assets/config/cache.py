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
    store: str = "database"

    # Cache stores
    #
    # The cache stores that are defined for your applications.
    # They can all be defined with environment variables in you `.env` file.
    # For instance:
    # >>> CACHE_STORES__DATABASE__DRIVER=database
    # >>> CACHE_STORES__DATABASE__CONNECTION=default
    stores: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: dict[str, dict[str, Any]](
            {
                "memory": {"driver": "memory"},
                "database": {
                    "driver": "database",
                    "connection": None,
                    "table": "cache",
                    "locker": {"store": "memory"},
                },
                "redis": {
                    "driver": "redis",
                    "connection": "cache",
                    "lock_connection": "default",
                    "locker": {"store": "memory"},
                    "l1_cache": {"store": {"driver": "memory"}},
                },
            }
        )
    )

    # Locker configuration
    #
    # The configuration for the locker that should be used by the cache stores to protect
    # against cache stampedes.
    # If not set, a default locker using an in-memory store will be used.
    # Use the `CACHE_LOCKER__STORE` environment variable to set this value in your `.env` file.
    # For instance:
    # >>> CACHE_LOCKER__STORE=memory
    locker: dict[str, Any] | None = None

    model_config = SettingsConfigDict(env_prefix="cache_", env_nested_delimiter="__")
