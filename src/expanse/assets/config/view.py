from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Config(BaseSettings):
    paths: list[Path] = Field(default=[Path("resources/views")])
    model_config = SettingsConfigDict(env_prefix="view_")
