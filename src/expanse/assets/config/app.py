from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Config(BaseSettings):
    # Application name

    # The name of the application.
    name: str = "Expanse"

    # Application environment
    #
    # The environment the application is running in.
    env: str = "production"

    # Application URL
    #
    # The URL of the application. This is used by some components of the application to generate URLs.
    # It should be set to the root URL of the application, including the scheme (http or https) and the domain name.
    # For instance: `https://example.com`.
    url: str = "http://localhost"

    # Debug mode
    #
    # The debug mode mostly controls how the application behaves when an error
    # occurs. When debug mode is enabled, the application will display detailed
    # messages about the error, including a stack trace. When debug mode is disabled,
    # the application will display a generic error message instead.
    debug: bool = False

    # Encryption key
    #
    # This key is used by the application for encryption and should be set
    # to a random, 32-character string or a base64-encoded 32 bytes prefixed with `base64:`.
    # This must be set prior to deploying the application.
    secret_key: SecretStr = SecretStr("")

    # Previous encryption keys
    #
    # This is a comma-separated list of previous encryption keys that were used by the
    # application. This is used to decrypt messages that were encrypted with an older key.
    previous_keys: SecretStr | None = None

    model_config = SettingsConfigDict(env_prefix="app_", env_nested_delimiter="__")
