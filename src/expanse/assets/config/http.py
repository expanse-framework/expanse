from typing import Annotated

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings import NoDecode
from pydantic_settings import SettingsConfigDict

from expanse.http.trusted_header import TrustedHeader


class Config(BaseSettings):
    trusted_proxies: Annotated[list[str], NoDecode] = Field(default_factory=list)
    trusted_headers: Annotated[list[TrustedHeader], NoDecode] = Field(
        default_factory=lambda: [
            TrustedHeader.X_FORWARDED_FOR,
            TrustedHeader.X_FORWARDED_HOST,
            TrustedHeader.X_FORWARDED_PORT,
            TrustedHeader.X_FORWARDED_PROTO,
        ]
    )
    trusted_hosts: Annotated[list[str], NoDecode] = Field(default_factory=list)

    model_config = SettingsConfigDict(env_prefix="http_")

    @field_validator("trusted_proxies", mode="before")
    @classmethod
    def decode_proxies(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, list):
            return v

        return [v.strip() for v in v.split(",")]

    @field_validator("trusted_headers", mode="before")
    @classmethod
    def decode_headers(cls, v: str | list[TrustedHeader]) -> list[TrustedHeader]:
        if isinstance(v, list):
            return v

        return [TrustedHeader(header.lower().strip()) for header in v.split(",")]

    @field_validator("trusted_hosts", mode="before")
    @classmethod
    def decode_hosts(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, list):
            return v

        return [v.strip() for v in v.split(",")]
