from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Config(BaseSettings):
    # Rate limiters
    #
    # The rate limiters that are defined for your applications.
    # They can all be defined with environment variables in you `.env` file.
    # For instance:
    # >>> RATE_LIMITING_LIMITERS__API__POLICY=sliding_window
    # >>> RATE_LIMITING_LIMITERS__API__LIMIT=100
    # >>> RATE_LIMITING_LIMITERS__API__INTERVAL="60s"
    limiters: dict[str, dict[str, Any]] = Field(default_factory=dict)

    model_config = SettingsConfigDict(
        env_prefix="rate_limiting_", env_nested_delimiter="__"
    )
