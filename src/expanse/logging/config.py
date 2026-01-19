from pathlib import Path
from typing import Annotated
from typing import Literal

from pydantic import Field
from pydantic import RootModel
from pydantic import field_validator
from pydantic_settings import BaseSettings


class BaseConfig(BaseSettings):
    enabled: bool = True
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    formatter: str | None = None


class StreamConfig(BaseConfig):
    driver: Literal["stream"] = "stream"

    stream: str = "stdout"


class ConsoleConfig(BaseConfig):
    driver: Literal["console"] = "console"


class FileConfig(BaseConfig):
    driver: Literal["file"] = "file"

    path: Path


class GroupConfig(BaseConfig):
    driver: Literal["group"] = "group"

    channels: list[str] = []

    @field_validator("channels", mode="before")
    @classmethod
    def decode_channels(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, list):
            return v

        return [v.strip() for v in v.split(",")]


class ChannelConfig(RootModel[StreamConfig | ConsoleConfig | FileConfig]):
    root: Annotated[
        StreamConfig | ConsoleConfig | FileConfig | GroupConfig,
        Field(discriminator="driver"),
    ]
