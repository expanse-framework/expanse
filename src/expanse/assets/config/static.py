from pathlib import Path

from pydantic import Field
from pydantic import HttpUrl
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from expanse.common.core.helpers import PlaceholderPath
from expanse.common.core.helpers import static_path


class Config(BaseSettings):
    url: HttpUrl | None = None
    prefix: str = "/static"
    paths: list[Path | PlaceholderPath] = Field(default=[static_path()])

    model_config = SettingsConfigDict(env_prefix="static_")
