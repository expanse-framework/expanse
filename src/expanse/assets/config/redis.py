from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Config(BaseSettings):
    # Default connection
    #
    # The default connection that should be used when no connection is explicitly specified.
    # Use the `REDIS_CONNECTION` environment variable to set this value in your `.env` file.
    # For instance:
    # >>> REDIS_CONNECTION=cache
    connection: str = "default"

    # Redis connections
    #
    # The Redis connections that are defined for your applications.
    # They can all be defined with environment variables in you `.env` file.
    # For instance:
    # >>> REDIS_CONNECTIONS__DEFAULT__URL=redis://127.0.0.1:6379/0
    connections: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "default": {
                "url": "redis://127.0.0.1:6379/0",
                "max_retries": 3,
                "backoff": {
                    "strategy": "decorrelated_jitter",
                    "base": 1,
                    "cap": 10,
                },
            },
            "cache": {
                "url": "redis://127.0.0.1:6379/1",
                "max_retries": 3,
                "backoff": {
                    "strategy": "decorrelated_jitter",
                    "base": 1,
                    "cap": 10,
                },
            },
        }
    )

    clusters: dict[str, dict[str, Any]] = {}

    model_config = SettingsConfigDict(env_prefix="redis_", env_nested_delimiter="__")
