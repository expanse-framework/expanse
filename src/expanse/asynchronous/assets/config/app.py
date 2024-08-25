from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from expanse.asynchronous.support.service_providers_list import ServiceProvidersList


class Config(BaseSettings):
    name: str = "Expanse"

    env: str = "production"

    debug: bool = False

    providers: list[str] = Field(
        default=(
            ServiceProvidersList.default()
            .merge(
                [
                    # Package-provided providers
                ]
            )
            .merge(
                [
                    # Console-specific providers
                ]
            )
            .to_list()
        )
    )

    model_config = SettingsConfigDict(env_prefix="app_")
