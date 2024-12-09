from typing import Literal

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from expanse.session.config import StoresConfig


class Config(BaseSettings):
    # Default session store
    #
    # The default session store that should be used
    # when no store is explicitly specified.
    #
    # Supported stores are: database and file
    store: Literal["database", "file", "dict", "null"] = "database"

    # Available session stores
    #
    # They can all be configured with environment variables in you `.env` file.
    # For instance:
    # >>> SESSION_STORES__DATABASE__TABLE=sessions
    # >>> SESSION_STORES__DATABASE__CONNECTION=named_connection
    stores: StoresConfig = StoresConfig()

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

    # Whether the session should be cleared when the browser is closed.
    #
    # When set to true, the session ID cookie will be removed after the user closes the browser window.
    clear_with_browser: bool = False

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

    model_config = SettingsConfigDict(env_prefix="session_", env_nested_delimiter="__")
