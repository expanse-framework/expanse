from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Config(BaseSettings):
    database: Path = Path("database")
    static: Path = Path("static")

    model_config = SettingsConfigDict(env_prefix="path_")
