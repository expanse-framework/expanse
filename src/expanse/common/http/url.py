import typing

from collections.abc import MutableMapping
from urllib.parse import SplitResult
from urllib.parse import urlsplit

from expanse.common.http.url_path import URLPath
from expanse.common.support._utils import string_matches


class URL:
    __slots__ = ("_url", "_components")

    def __init__(
        self,
        url: str = "",
        *,
        scope: MutableMapping[str, typing.Any] | None = None,
        environ: MutableMapping[str, typing.Any] | None = None,
        **components: typing.Any,
    ) -> None:
        if components:
            assert not url, 'Cannot set both "url" and "**components".'
            url = URL("").replace(**components).components.geturl()
        elif scope is not None:
            scheme = scope.get("scheme", "http")
            server = scope.get("server", None)
            path = scope.get("root_path", "") + scope["path"]
            query_string = scope.get("query_string", b"")

            host_header = None
            for key, value in scope["headers"]:
                if key == b"host":
                    host_header = value.decode("latin-1")
                    break
            url = self._build_url(scheme, path, query_string, server, host_header)
        elif environ is not None:
            scheme = environ["wsgi.url_scheme"]
            server = (environ["SERVER_NAME"], int(environ["SERVER_PORT"]))
            path = (
                (environ.get("SCRIPT_NAME", "") + environ.get("PATH_INFO", ""))
                .encode("latin1")
                .decode("utf8")
            )
            query_string = environ.get("QUERY_STRING", "").encode("latin-1")
            host_header = environ.get("HTTP_HOST", None)
            url = self._build_url(scheme, path, query_string, server, host_header)

        self._url = url
        self._components = urlsplit(url)

    def _build_url(
        self,
        scheme: str,
        path: str,
        query_string: bytes = b"",
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
            url = f"{url}?{query_string.decode()}"

        return url

    @property
    def components(self) -> SplitResult:
        return self._components

    @property
    def scheme(self) -> str:
        return self.components.scheme

    @property
    def netloc(self) -> str:
        return self.components.netloc

    @property
    def path(self) -> str:
        return URLPath(self.components.path)

    @property
    def query(self) -> str:
        return self.components.query

    @property
    def fragment(self) -> str:
        return self.components.fragment

    @property
    def username(self) -> str | None:
        return self.components.username

    @property
    def password(self) -> str | None:
        return self.components.password

    @property
    def hostname(self) -> str | None:
        return self.components.hostname

    @property
    def port(self) -> int | None:
        return self.components.port

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

        components = self.components._replace(**kwargs)
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
