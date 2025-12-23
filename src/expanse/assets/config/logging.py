from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from expanse.logging.config import ChannelConfig
from expanse.logging.config import FileConfig
from expanse.logging.config import StreamConfig


class Config(BaseSettings):
    # Default channel
    #
    # The channel that should be used when no channel is explicitly specified.
    default: str = Field(validation_alias="log_channel", default="stream")

    # Channels
    #
    # The logging channels that are defined for your applications.
    # They can all be defined with environment variables in you `.env` file.
    # For instance:
    # >>> LOG_CHANNELS__STREAM__DRIVER=stream
    # >>> DB_CONNECTIONS__STREAM__STREAM=stdout
    # >>> DB_CONNECTIONS__STREAM__LEVEL=INFO
    channels: dict[str, ChannelConfig] = Field(
        default_factory=lambda: {
            "stream": StreamConfig(stream="stdout"),
            "file": FileConfig(path=Path("log/app.log")),
        }
    )

    model_config = SettingsConfigDict(env_prefix="LOG_", env_nested_delimiter="__")
