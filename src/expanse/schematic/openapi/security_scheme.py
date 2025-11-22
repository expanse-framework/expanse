from __future__ import annotations

from typing import Any
from typing import Literal


class OAuthFlow:
    """
    Configuration details for a supported OAuth Flow.
    """

    def __init__(
        self,
        authorization_url: str | None = None,
        token_url: str | None = None,
        refresh_url: str | None = None,
        scopes: dict[str, str] | None = None,
    ) -> None:
        self.authorization_url: str | None = authorization_url
        self.token_url: str | None = token_url
        self.refresh_url: str | None = refresh_url
        self.scopes: dict[str, str] = scopes or {}

    def set_authorization_url(self, url: str) -> OAuthFlow:
        self.authorization_url = url
        return self

    def set_token_url(self, url: str) -> OAuthFlow:
        self.token_url = url
        return self

    def set_refresh_url(self, url: str) -> OAuthFlow:
        self.refresh_url = url
        return self

    def add_scope(self, name: str, description: str) -> OAuthFlow:
        self.scopes[name] = description
        return self

    def set_scopes(self, scopes: dict[str, str]) -> OAuthFlow:
        self.scopes = scopes
        return self

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if self.authorization_url is not None:
            result["authorizationUrl"] = self.authorization_url

        if self.token_url is not None:
            result["tokenUrl"] = self.token_url

        if self.refresh_url is not None:
            result["refreshUrl"] = self.refresh_url

        if self.scopes:
            result["scopes"] = self.scopes

        return result


class OAuthFlows:
    """
    Allows configuration of the supported OAuth Flows.
    """

    def __init__(self) -> None:
        self.implicit: OAuthFlow | None = None
        self.password: OAuthFlow | None = None
        self.client_credentials: OAuthFlow | None = None
        self.authorization_code: OAuthFlow | None = None

    def set_implicit(self, flow: OAuthFlow) -> OAuthFlows:
        self.implicit = flow
        return self

    def set_password(self, flow: OAuthFlow) -> OAuthFlows:
        self.password = flow
        return self

    def set_client_credentials(self, flow: OAuthFlow) -> OAuthFlows:
        self.client_credentials = flow
        return self

    def set_authorization_code(self, flow: OAuthFlow) -> OAuthFlows:
        self.authorization_code = flow
        return self

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if self.implicit is not None:
            result["implicit"] = self.implicit.to_dict()

        if self.password is not None:
            result["password"] = self.password.to_dict()

        if self.client_credentials is not None:
            result["clientCredentials"] = self.client_credentials.to_dict()

        if self.authorization_code is not None:
            result["authorizationCode"] = self.authorization_code.to_dict()

        return result


class SecurityScheme:
    """
    Defines a security scheme that can be used by the operations.

    Supported schemes are HTTP authentication, an API key (either as a header, a cookie parameter
    or as a query parameter), mutual TLS (use of a client certificate), OAuth2's common flows
    (implicit, password, client credentials and authorization code) as defined in RFC6749,
    and OpenID Connect Discovery.
    """

    def __init__(
        self,
        type: Literal["apiKey", "http", "mutualTLS", "oauth2", "openIdConnect"],
        **kwargs,
    ) -> None:
        self.type: Literal["apiKey", "http", "mutualTLS", "oauth2", "openIdConnect"] = (
            type
        )
        self.description: str | None = None

        # apiKey specific fields
        self.name: str | None = None
        self.in_: Literal["query", "header", "cookie"] | None = None

        # http specific fields
        self.scheme: str | None = None
        self.bearer_format: str | None = None

        # oauth2 specific fields
        self.flows: OAuthFlows | None = None

        # openIdConnect specific fields
        self.open_id_connect_url: str | None = None

        # Set fields based on kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def api_key(
        cls,
        name: str,
        in_: Literal["query", "header", "cookie"],
        description: str | None = None,
    ) -> SecurityScheme:
        scheme = cls("apiKey")
        scheme.name = name
        scheme.in_ = in_
        scheme.description = description
        return scheme

    @classmethod
    def http(
        cls,
        scheme: str,
        bearer_format: str | None = None,
        description: str | None = None,
    ) -> SecurityScheme:
        security_scheme = cls("http")
        security_scheme.scheme = scheme
        security_scheme.bearer_format = bearer_format
        security_scheme.description = description
        return security_scheme

    @classmethod
    def mutual_tls(cls, description: str | None = None) -> SecurityScheme:
        scheme = cls("mutualTLS")
        scheme.description = description
        return scheme

    @classmethod
    def oauth2(
        cls, flows: OAuthFlows, description: str | None = None
    ) -> SecurityScheme:
        scheme = cls("oauth2")
        scheme.flows = flows
        scheme.description = description
        return scheme

    @classmethod
    def open_id_connect(
        cls, open_id_connect_url: str, description: str | None = None
    ) -> SecurityScheme:
        scheme = cls("openIdConnect")
        scheme.open_id_connect_url = open_id_connect_url
        scheme.description = description
        return scheme

    def set_description(self, description: str) -> SecurityScheme:
        self.description = description
        return self

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"type": self.type}

        if self.description is not None:
            result["description"] = self.description

        # apiKey specific fields
        if self.type == "apiKey":
            if self.name is not None:
                result["name"] = self.name
            if self.in_ is not None:
                result["in"] = self.in_

        # http specific fields
        elif self.type == "http":
            if self.scheme is not None:
                result["scheme"] = self.scheme
            if self.bearer_format is not None:
                result["bearerFormat"] = self.bearer_format

        # oauth2 specific fields
        elif self.type == "oauth2":
            if self.flows is not None:
                result["flows"] = self.flows.to_dict()

        # openIdConnect specific fields
        elif self.type == "openIdConnect":
            if self.open_id_connect_url is not None:
                result["openIdConnectUrl"] = self.open_id_connect_url

        return result
