from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Config(BaseSettings):
    connection: str = "default"

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

    model_config = SettingsConfigDict(env_prefix="REDIS_", env_nested_delimiter="__")
