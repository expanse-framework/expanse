from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Config(BaseSettings):
    paths: list[str] = ["api/*"]
    allowed_methods: list[str] = ["*"]
    allowed_origins: list[str] = ["*"]
    allowed_origins_patterns: list[str] = []
    allowed_headers: list[str] = ["*"]
    exposed_headers: list[str] = ["*"]
    max_age: int = 0
    supports_credentials: bool = False

    model_config = SettingsConfigDict(env_prefix="cors_")
