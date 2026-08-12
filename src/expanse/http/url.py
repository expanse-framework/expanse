"""URL facade.

The parsing (scheme/netloc/path/query/…) is implemented in the Rust
extension when available; the Python fallback lives at
``expanse.http._python.url``. Higher-level operations that don't benefit
from being in Rust (``from_scope``, ``from_components``, ``replace``,
returning ``URLPath`` from ``.path``) sit in this thin subclass so both
backends share the same conveniences.
"""

from __future__ import annotations

import typing

from typing import Any
from typing import Self
from urllib.parse import SplitResult
from urllib.parse import urlsplit

from expanse.http._backend import _rust
from expanse.http._python.url import QueryParameters
from expanse.http.url_path import URLPath
from expanse.support._utils import string_matches


if typing.TYPE_CHECKING:
    from expanse.types import Scope


_DEFAULT_PORTS = {"http": 80, "https": 443, "ws": 80, "wss": 443}


def _build_url(
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
        default_port = _DEFAULT_PORTS[scheme]
        if port == default_port or port is None:
            url = f"{scheme}://{host}{path}"
        else:
            url = f"{scheme}://{host}:{port}{path}"

    if query_string:
        query_string = (
            query_string.decode() if isinstance(query_string, bytes) else query_string
        )
        url = f"{url}?{query_string}"

    return url


if _rust is not None:
    _URLBase = _rust.URL
else:
    from expanse.http._python.url import (  # type: ignore[no-redef]
        URL as _URLBase,  # noqa: N811
    )


class URL(_URLBase):  # type: ignore[misc, valid-type]
    """URL wrapping the Rust parser (or Python fallback).

    Adds ``from_scope`` / ``from_components`` / ``replace`` /
    ``is_`` / ``path_is``, and wraps ``.path`` in :class:`URLPath`.
    """

    @classmethod
    def from_scope(cls, scope: Scope) -> Self:
        scheme = scope.get("scheme", "http")
        server = scope.get("server", None)
        path = scope.get("root_path", "") + scope["path"]
        query_string = scope.get("query_string", b"")

        host_header: str | None = None
        for key, value in scope["headers"]:
            if key == b"host":
                host_header = value.decode("latin-1")
                break

        return cls(_build_url(scheme, path, query_string, server, host_header))

    @classmethod
    def from_components(cls, **components: Any) -> Self:
        return cls(cls("").replace(**components).components.geturl())

    @property
    def path(self) -> URLPath:  # type: ignore[override]
        return URLPath(super().path)

    @property
    def components(self) -> SplitResult:
        # Kept for backwards compatibility with call sites that peek at the
        # urllib.parse SplitResult. We recompute rather than cache to keep
        # the Rust/Python surfaces uniform.
        return urlsplit(str(self))

    def is_(self, pattern: str | list[str]) -> bool:
        return string_matches(str(self), pattern)

    def path_is(self, pattern: str | list[str]) -> bool:
        return string_matches(str(self.path).lstrip("/"), pattern)

    def replace(self, **kwargs: Any) -> Self:
        if any(k in kwargs for k in ("username", "password", "hostname", "port")):
            hostname = kwargs.pop("hostname", None)
            port = kwargs.pop("port", self.port)
            username = kwargs.pop("username", self.username)
            password = kwargs.pop("password", self.password)

            if hostname is None:
                netloc = self.netloc
                _, _, hostname = netloc.rpartition("@")
                if hostname[-1:] != "]":
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

        components = urlsplit(str(self))._replace(**kwargs)
        return self.__class__(components.geturl())


__all__ = ["URL", "QueryParameters"]
