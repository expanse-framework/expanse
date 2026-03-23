from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from expanse.messenger.config import TransportConfig
from expanse.messenger.retry.config import RetryStrategyConfig
from expanse.messenger.retry.multiplier.config import MultiplierRetryStrategyConfig
from expanse.messenger.transports.memory.config import MemoryTransportConfig
from expanse.messenger.transports.sync.config import SyncTransportConfig


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
    transports: dict[str, TransportConfig] = Field(
        default_factory=lambda: {
            "sqlite": TransportConfig(root=SyncTransportConfig()),
            "memory": TransportConfig(root=MemoryTransportConfig()),
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
    retry_strategies: dict[str, RetryStrategyConfig] = Field(
        default_factory=lambda: {
            "multiplier": RetryStrategyConfig(root=MultiplierRetryStrategyConfig())
        }
    )

    model_config = SettingsConfigDict(
        env_prefix="messenger_", env_nested_delimiter="__"
    )
