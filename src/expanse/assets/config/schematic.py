from typing import ClassVar

from pydantic import BaseModel
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class APIInfo(BaseModel):
    version: str = "0.0.1"

    description: str = ""


class Config(BaseSettings):
    # URL path for the API.
    # By default, all routes prefixed with this path will be considered part of the API
    # and be added to the documentation.
    api_path: str = "/api"

    info: APIInfo = APIInfo()

    # The default export path for the OpenAPI schema file.
    export_path: str = "api.json"

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="SCHEMATIC_", env_nested_delimiter="__"
    )
