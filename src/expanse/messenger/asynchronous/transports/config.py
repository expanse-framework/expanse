from pydantic_settings import BaseSettings


class BaseTransportConfig(BaseSettings):
    retry_strategy: str | None = "multiplier"
