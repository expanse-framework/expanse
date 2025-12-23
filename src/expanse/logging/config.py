from pathlib import Path
from typing import Annotated
from typing import Literal

from pydantic import Field
from pydantic import RootModel
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


class ChannelConfig(RootModel[StreamConfig | ConsoleConfig | FileConfig]):
    root: Annotated[
        StreamConfig | ConsoleConfig | FileConfig, Field(discriminator="driver")
    ]
