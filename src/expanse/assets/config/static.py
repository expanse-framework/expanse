from pathlib import Path

from pydantic import Field
from pydantic import HttpUrl
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Config(BaseSettings):
    url: HttpUrl | None = None
    prefix: str = "/static"
    paths: list[Path] = Field(default=[Path("static")])

    model_config = SettingsConfigDict(env_prefix="static_")
