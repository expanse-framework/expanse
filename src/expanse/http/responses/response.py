from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Generic
from typing import Self
from typing import TypeAlias
from typing import TypeVar
from typing import overload

from expanse.http.cookie import Cookie
from expanse.http.cookie import SameSite
from expanse.http.header_bag import HeaderBag


if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import MutableMapping
    from datetime import datetime

    from expanse.http.request import Request
    from expanse.types import Receive
    from expanse.types import Scope
    from expanse.types import Send


T = TypeVar("T")
Cookies: TypeAlias = dict[str, Cookie]


class Response(Generic[T]):
    __slots__ = ("content_type", "cookies", "headers", "status_code")

    content: T

    def __init__(
        self,
        content: T,
        *,
        status_code: int = 200,
        headers: MutableMapping[str, str] | None = None,
        content_type: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.content_type = content_type
        self.headers = HeaderBag(headers or {})
        self.cookies: dict[str, Cookie] = {}

    def with_status(self, status_code: int) -> Self:
        self.status_code = status_code

        return self

    def with_header(self, key: str, value: str) -> Self:
        self.headers[key] = value

        return self

    def with_headers(self, headers: Mapping[str, str]) -> Self:
        self.headers.update(headers)

        return self

    @overload
    def with_cookie(self, /, cookie: Cookie) -> Self:
        """
        :param cookie: The cookie to add to the response.
        """

    @overload
    def with_cookie(
        self,
        name: str,
        value: str | None = None,
        expires: int | datetime = 0,
        domain: str | None = None,
        path: str | None = None,
        secure: bool | None = None,
        http_only: bool = False,
        same_site: SameSite = SameSite.LAX,
        partitioned: bool = False,
    ) -> Self:
        """
        :param name: The name of the cookie.
        :param value: The value of the cookie.
        :param expires: The time the cookie expires.
        :param domain: The domain the cookie is available to.
        :param path: The path on the server in which the cookie will be available on.
        :param secure: Whether the client should send back the cookie only over HTTPS
                       or None to auto-enable this when the request is already using HTTPS.
        :param http_only: Whether the cookie will be made accessible only through the HTTP protocol.
        :param same_site: Whether the cookie will be available for cross-site requests.
        :param partitioned: Whether the cookie is partitioned or not.
        """

    def with_cookie(
        self,
        name: str | Cookie,
        value: str | None = None,
        expires: int | datetime = 0,
        domain: str | None = None,
        path: str | None = None,
        secure: bool | None = None,
        http_only: bool = False,
        same_site: SameSite = SameSite.LAX,
        partitioned: bool = False,
    ) -> Self:
        """
        :param name: The name of the cookie.
        :param value: The value of the cookie.
        :param expires: The time the cookie expires.
        :param domain: The domain the cookie is available to.
        :param path: The path on the server in which the cookie will be available on.
        :param secure: Whether the client should send back the cookie only over HTTPS
                       or None to auto-enable this when the request is already using HTTPS.
        :param http_only: Whether the cookie will be made accessible only through the HTTP protocol.
        :param same_site: Whether the cookie will be available for cross-site requests.
        :param partitioned: Whether the cookie is partitioned or not.
        """
        if isinstance(name, Cookie):
            self.cookies[name.name] = name

            return self

        self.cookies[name] = Cookie(
            name,
            value,
            expires=expires,
            domain=domain,
            path=path,
            secure=secure,
            http_only=http_only,
            same_site=same_site,
            partitioned=partitioned,
        )

        return self

    async def prepare(self, request: Request) -> None:
        self._response.list_headers = self._list_headers  # type: ignore[method-assign]

        is_request_secure = request.is_secure()

        for cookie in self.cookies.values():
            if is_request_secure:
                cookie.set_secure_default(is_request_secure)

    def _list_headers(self, *, as_bytes):
        """
        Patched version of Baize's list_headers method to support our own cookies.
        """
        if as_bytes:
            return [
                *(
                    (key.encode("latin-1"), value.encode("latin-1"))
                    for key, value in self.headers.items()
                ),
                *((b"set-cookie", bytes(cookie)) for cookie in self._cookies.values()),
            ]
        else:
            return [
                *self.headers.items(),
                *(("set-cookie", str(cookie)) for cookie in self._cookies.values()),
            ]

    def _encode_headers(self) -> list[tuple[bytes, bytes]]:
        """
        Encodes the headers to a list of tuples with bytes.
        """
        return [
            (key.encode("latin-1"), value.encode("latin-1"))
            for key, value in self.headers.items()
        ] + [(b"set-cookie", bytes(cookie)) for cookie in self.cookies.values()]

    async def start_response(self, send: Send) -> None:
        """
        Starts the response by sending the status line and headers.
        This method should be called before sending the body.
        """
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.headers.encode(),
            }
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        return await self._response(scope=scope, receive=receive, send=send)
