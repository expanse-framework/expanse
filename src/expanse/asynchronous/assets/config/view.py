from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from expanse.common.core.helpers import PlaceholderPath
from expanse.common.core.helpers import resource_path


class Config(BaseSettings):
    paths: list[Path | PlaceholderPath] = Field(default=[resource_path("views")])
    model_config = SettingsConfigDict(env_prefix="view_")
