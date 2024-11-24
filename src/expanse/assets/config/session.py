from typing import Literal

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Config(BaseSettings):
    # Default session store
    #
    # The default session store that should be used
    # when no store is explicitly specified.
    #
    # Supported stores are: database and file
    store: Literal["database", "file", "dict"] = "database"

    # Session cookie name
    #
    # The name of the session cookie.
    # Leaving it to none — which is the default — will drive the name from your application name.
    name: str | None = None

    # Session lifetime
    #
    # This option defines maximum duration the session can remain idle
    # before it expires.
    lifetime: int = 120

    # Session database connection
    #
    # The database connection that should be used to store the session data.
    # The value must match one of the configured database connections.
    database_connection: str | None = None

    # Session database table
    #
    # The table that should be used to store the session data.
    database_table: str = "sessions"

    # Session cookie path
    #
    # The path for which the session cookie is available.
    path: str = "/"

    # Session cookie domain
    #
    # The domain for which the session cookie is available.
    domain: str | None = None

    # Session cookie secure
    #
    # Whether the session cookie should only be sent over HTTPS.
    secure: bool = False

    # Session cookie http only
    #
    # Setting this to true will prevent JavaScript from accessing the session cookie.
    http_only: bool = True

    # Session cookie same site
    #
    # The SameSite attribute of the session cookie.
    # This determines the behavior of the cookie in case of cross-site requests
    # and is useful in preventing CSRF attacks.
    #
    # Supported values are: strict, lax, and none
    same_site: Literal["strict", "lax", "none"] = "lax"

    model_config = SettingsConfigDict(env_prefix="session_")
