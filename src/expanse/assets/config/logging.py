from pathlib import Path
from typing import Any
from typing import Literal

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


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
    # >>> LOG_CHANNELS__STREAM__STREAM=stdout
    # >>> LOG_CHANNELS__STREAM__LEVEL=INFO
    channels: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: dict[str, dict[str, Any]](
            {
                "stream": {
                    "driver": "stream",
                    "stream": "stderr",
                    "level": "INFO",
                },
                "file": {
                    "driver": "file",
                    "path": Path("storage/log/app.log"),
                    "level": "INFO",
                },
                "console": {
                    "driver": "console",
                    "level": "DEBUG",
                },
                "group": {
                    "driver": "group",
                    "channels": ["stream", "file"],
                    "level": "INFO",
                },
            }
        )
    )

    # Logging mode
    #
    # Whether the logging manager should operate in sync or async mode.
    # In sync mode, log messages are processed synchronously,
    # which can impact performance but ensures that logs are written immediately and sequentially.
    # This can be useful when debugging.
    # >>> LOG_SYNC=true
    mode: Literal["sync", "async"] = "async"

    routing: dict[str, list[str]] = Field(default_factory=dict)

    model_config = SettingsConfigDict(env_prefix="LOG_", env_nested_delimiter="__")

    @field_validator("routing", mode="before")
    @classmethod
    def decode_channels(
        cls, v: dict[str, str] | dict[str, list[str]]
    ) -> dict[str, list[str]]:
        new_v: dict[str, list[str]] = {}
        for key, value in v.items():
            if isinstance(value, str):
                new_v[key] = [v.strip() for v in value.split(",")]
            else:
                new_v[key] = value

        return new_v
