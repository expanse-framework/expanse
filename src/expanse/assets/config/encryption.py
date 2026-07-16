from typing import Annotated

from pydantic_settings import BaseSettings
from pydantic_settings import NoDecode
from pydantic_settings import SettingsConfigDict

from expanse.support.secret import Secret


class Config(BaseSettings):
    # The cipher method used for encryption. Currently, only aes-256-gcm is supported.
    cipher: str = "aes-256-gcm"

    # The salt used for encryption key derivation.
    salt: Annotated[Secret[str], NoDecode] = Secret("")

    # Whether to store key references in the encrypted message.
    # This is useful for key rotation, as it allows the decryptor
    # to determine which key was used to encrypt the message.
    store_key_references: bool = False

    model_config = SettingsConfigDict(env_prefix="encryption_")
