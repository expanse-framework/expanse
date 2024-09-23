from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Config(BaseSettings):
    # The cipher method used for encryption. Currently, only aes-256-gcm is supported.
    cipher: str = "aes-256-gcm"

    # The salt used for encryption key derivation.
    salt: SecretStr = SecretStr("")

    model_config = SettingsConfigDict(env_prefix="encryption_")
