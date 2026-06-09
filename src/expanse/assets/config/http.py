from typing import Annotated

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings import NoDecode
from pydantic_settings import SettingsConfigDict

from expanse.http.trusted_header import TrustedHeader


class Config(BaseSettings):
    # Trusted proxies
    #
    # The list of trusted proxies that should be used by the application to determine the client's IP address
    # and other information when the application is behind a proxy.
    # Use the `HTTP_TRUSTED_PROXIES` environment variable to set this value in your `.env` file.
    # For instance:
    # >>> HTTP_TRUSTED_PROXIES=192.168.0.1,192.168.0.2
    trusted_proxies: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # Trusted headers
    #
    # The list of trusted headers that should be used by the application to determine the client's IP address
    # and other information when the application is behind a proxy.
    # Use the `HTTP_TRUSTED_HEADERS` environment variable to set this value in your `.env` file.
    # For instance:
    # >>> HTTP_TRUSTED_HEADERS=X-Forwarded-For,X-Forwarded-Host,X-Forwarded-Port,X-Forwarded-Proto
    trusted_headers: Annotated[list[TrustedHeader], NoDecode] = Field(
        default_factory=lambda: [
            TrustedHeader.X_FORWARDED_FOR,
            TrustedHeader.X_FORWARDED_HOST,
            TrustedHeader.X_FORWARDED_PORT,
            TrustedHeader.X_FORWARDED_PROTO,
        ]
    )

    # Trusted hosts
    # The list of trusted hosts that should be used by the application
    # to determine if the Host header of incoming requests is valid.
    # Use the `HTTP_TRUSTED_HOSTS` environment variable to set this value in your `.env` file.
    # For instance:
    # >>> HTTP_TRUSTED_HOSTS=example.com,*.example.com
    trusted_hosts: Annotated[list[str], NoDecode] = Field(default_factory=list)

    model_config = SettingsConfigDict(env_prefix="http_", env_nested_delimiter="__")

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
