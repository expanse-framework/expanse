from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from expanse.http.trusted_header import TrustedHeader


class Config(BaseSettings):
    trusted_proxies: list[str] = Field(default_factory=list)
    trusted_headers: list[TrustedHeader] = Field(
        default_factory=lambda: [
            TrustedHeader.X_FORWARDED_FOR,
            TrustedHeader.X_FORWARDED_HOST,
            TrustedHeader.X_FORWARDED_PORT,
            TrustedHeader.X_FORWARDED_PROTO,
        ]
    )

    model_config = SettingsConfigDict(env_prefix="http_")
