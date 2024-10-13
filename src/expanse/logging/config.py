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

    stream: str = "sys.stdout"


class ConsoleConfig(BaseConfig):
    driver: Literal["console"] = "console"


class ChannelConfig(RootModel[StreamConfig | ConsoleConfig]):
    root: Annotated[StreamConfig | ConsoleConfig, Field(discriminator="driver")]
