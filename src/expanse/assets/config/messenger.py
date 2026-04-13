from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Config(BaseSettings):
    # Default transport
    #
    # The default transport that should be used
    # when no transport is explicitly specified.
    transport: str = "sync"

    # Failure transport
    #
    # The transport where messages that failed to be processed should be sent.
    failure_transport: str | None = None

    # Transports
    #
    # The transports that are defined for your applications.
    # They can all be defined with environment variables in you `.env` file.
    # For instance:
    # >>> TRANSPORTS__MEMORY__DRIVER=memory
    transports: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "sync": {"driver": "sync"},
            "memory": {"driver": "memory"},
        }
    )

    # Retry strategies
    #
    # The retry strategies that are defined for your application.
    # They can all be defined with environment variables in you `.env` file.
    # For instance:
    # >>> RETRY_STRATEGIES__MULTIPLIER__TYPE=multiplier
    # >>> RETRY_STRATEGIES__MULTIPLIER__DELAY=1000
    # >>> RETRY_STRATEGIES__MULTIPLIER__MULTIPLIER=2
    retry_strategies: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "multiplier": {
                "type": "multiplier",
                "max_retries": 3,
                "delay": 1000,
                "multiplier": 2,
                "max_delay": None,
                "jitter": 0.1,
            }
        }
    )

    model_config = SettingsConfigDict(
        env_prefix="messenger_", env_nested_delimiter="__"
    )
