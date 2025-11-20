import typing

from typing import Self
from urllib.parse import SplitResult
from urllib.parse import parse_qs
from urllib.parse import urlencode
from urllib.parse import urlsplit

from expanse.http.url_path import URLPath
from expanse.support._utils import string_matches
from expanse.types import Scope


class QueryParameters:
    def __init__(self, query_string: str) -> None:
        self._params: dict[str, list[str]] = parse_qs(query_string)

    def set(self, key: str, value: str | list[str]) -> Self:
        if isinstance(value, str):
            value = [value]

        self._params[key] = value

        return self

    def append(self, key: str, value: str | list[str]) -> Self:
        if isinstance(value, str):
            value = [value]

        if key not in self._params:
            self._params[key] = []

        self._params[key].extend(value)

        return self

    def remove(self, key: str) -> Self:
        if key in self._params:
            del self._params[key]

        return self

    def __str__(self) -> str:
        return urlencode(self._params, doseq=True)

    def __bool__(self) -> bool:
        return bool(self._params)


class URL:
    __slots__ = ("_components", "_url")

    def __init__(self, url: str = "") -> None:
        self._url: str = url
        self._components: SplitResult = urlsplit(url)

    @classmethod
    def from_scope(cls, scope: Scope) -> "URL":
        """
        Create a URL instance from an ASGI scope.
        """
        scheme = scope.get("scheme", "http")
        server = scope.get("server", None)
        path = scope.get("root_path", "") + scope["path"]
        query_string = scope.get("query_string", b"")

        host_header = None
        for key, value in scope["headers"]:
            if key == b"host":
                host_header = value.decode("latin-1")
                break
        url = cls._build_url(scheme, path, query_string, server, host_header)

        return cls(url)

    @classmethod
    def from_components(cls, **components: typing.Any) -> "URL":
        """
        Create a URL instance from components.
        """
        url = URL("").replace(**components).components.geturl()

        return cls(url)

    @classmethod
    def _build_url(
        cls,
        scheme: str,
        path: str,
        query_string: bytes | str = b"",
        server: tuple[str, int | None] | None = None,
        host_header: str | None = None,
    ) -> str:
        if host_header is not None:
            url = f"{scheme}://{host_header}{path}"
        elif server is None:
            url = path
        else:
            host, port = server
            default_port = {"http": 80, "https": 443, "ws": 80, "wss": 443}[scheme]
            if port == default_port or port is None:
                url = f"{scheme}://{host}{path}"
            else:
                url = f"{scheme}://{host}:{port}{path}"

        if query_string:
            query_string = (
                query_string.decode()
                if isinstance(query_string, bytes)
                else query_string
            )
            url = f"{url}?{query_string}"

        return url

    @property
    def components(self) -> SplitResult:
        return self._components

    @property
    def full(self) -> str:
        return self._url

    @property
    def scheme(self) -> str:
        return self._components.scheme

    @property
    def netloc(self) -> str:
        return self._components.netloc

    @property
    def path(self) -> str:
        p = URLPath(self._components.path)

        return p

    @property
    def query(self) -> str:
        return self._components.query

    @property
    def fragment(self) -> str:
        return self._components.fragment

    @property
    def username(self) -> str | None:
        return self._components.username

    @property
    def password(self) -> str | None:
        return self._components.password

    @property
    def hostname(self) -> str | None:
        return self._components.hostname

    @property
    def port(self) -> int | None:
        return self._components.port

    def is_secure(self) -> bool:
        return self.scheme == "https"

    def is_(self, pattern: str | list[str]) -> bool:
        """
        Determine if the full URL matches a given pattern.
        """
        return string_matches(self._url, pattern)

    def path_is(self, pattern: str | list[str]) -> bool:
        """
        Determine if the full URL matches a given pattern.
        """
        return string_matches(self.path.lstrip("/"), pattern)

    def replace(self, **kwargs: typing.Any) -> "URL":
        if (
            "username" in kwargs
            or "password" in kwargs
            or "hostname" in kwargs
            or "port" in kwargs
        ):
            hostname = kwargs.pop("hostname", None)
            port = kwargs.pop("port", self.port)
            username = kwargs.pop("username", self.username)
            password = kwargs.pop("password", self.password)

            if hostname is None:
                netloc = self.netloc
                _, _, hostname = netloc.rpartition("@")

                if hostname[-1] != "]":
                    hostname = hostname.rsplit(":", 1)[0]

            netloc = hostname
            if port is not None:
                netloc += f":{port}"
            if username is not None:
                userpass = username
                if password is not None:
                    userpass += f":{password}"
                netloc = f"{userpass}@{netloc}"

            kwargs["netloc"] = netloc

        components = self._components._replace(**kwargs)
        return self.__class__(components.geturl())

    def __eq__(self, other: typing.Any) -> bool:
        return str(self) == str(other)

    def __str__(self) -> str:
        return self._url

    def __repr__(self) -> str:
        url = str(self)
        if self.password:
            url = str(self.replace(password="********"))
        return f"{self.__class__.__name__}({url!r})"
