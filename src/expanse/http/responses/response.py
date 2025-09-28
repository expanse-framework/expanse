from __future__ import annotations

import asyncio

from typing import TYPE_CHECKING
from typing import Self
from typing import TypeVar
from typing import overload

from expanse.http.cookie import Cookie
from expanse.http.cookie import SameSite
from expanse.http.response_header_bag import ResponseHeaderBag
from expanse.support._concurrency import run_in_threadpool


if TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable
    from collections.abc import Mapping
    from datetime import datetime

    from expanse.container.container import Container
    from expanse.http.request import Request
    from expanse.types import Receive
    from expanse.types import Send


T = TypeVar("T")
type Cookies = dict[str, Cookie]


class Response:
    __slots__ = (
        "_body",
        "_content",
        "_deferred",
        "_prepared",
        "_rendered",
        "content_type",
        "cookies",
        "encoding",
        "headers",
        "status_code",
    )

    def __init__(
        self,
        content: bytes | str | None = None,
        status_code: int = 200,
        *,
        headers: Mapping[str, str] | None = None,
        content_type: str | None = None,
        encoding: str = "utf-8",
    ) -> None:
        self._content: bytes | str | None = content
        self.status_code: int = status_code
        self.content_type: str | None = content_type
        self.encoding: str = encoding
        self.headers: ResponseHeaderBag = ResponseHeaderBag(headers or {})
        self.cookies: dict[str, Cookie] = {}
        self._prepared: bool = False
        self._rendered: bool = False
        self._body: bytes | None = None
        self._deferred: list[Callable[[], None] | Callable[[], Awaitable[None]]] = []

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
    def with_cookie(self, /, name: Cookie) -> Self:
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

    def defer(self, func: Callable[[], None] | Callable[[], Awaitable[None]]) -> Self:
        """
        Defers the running of a function after the response is sent.

        :param func: A callable that will be executed after the response is sent.
        """
        self._deferred.append(func)

        return self

    async def prepare(self, request: Request, container: Container) -> None:
        """
        Prepares the response before sending it to the client.

        This makes sure that the response is compliant with RFC 2616.

        :param request: The current request being processed.
        """
        if self._prepared:
            return

        body = await self.render()

        headers = self.headers
        is_request_secure = request.is_secure()

        if not headers.has("Content-Type"):
            if self.content_type is not None:
                headers.set(
                    "Content-Type",
                    self.content_type
                    if not self.content_type.startswith("text/")
                    else f"{self.content_type}; charset={self.encoding}",
                )
            else:
                headers.set("Content-Type", f"text/plain; charset={self.encoding}")

        if not headers.has("Content-Length") and body is not None:
            headers.set("Content-Length", str(len(body)))

        if self.is_informational() or self.is_empty():
            self._body = None
            headers.remove("Content-Type")
            headers.remove("Content-Length")
        else:
            if request.method == "HEAD":
                self._body = None

        for cookie in self.cookies.values():
            if is_request_secure:
                cookie.set_secure_default(is_request_secure)

        self._prepared = True

    def encode_headers(self) -> list[tuple[bytes, bytes]]:
        """
        Encodes the headers to a list of tuples with bytes.
        """
        return self.headers.encode() + [
            (b"set-cookie", bytes(cookie)) for cookie in self.cookies.values()
        ]

    async def render(self) -> bytes | None:
        """
        Renders the response content to bytes.
        """
        if self._rendered:
            return self._body

        if isinstance(self._content, bytes):
            self._body = self._content

        elif isinstance(self._content, str):
            self._body = self._content.encode("utf-8")

        self._rendered = True

        return self._body

    def is_empty(self) -> bool:
        """
        Checks if the response is considered empty, based on the status code.
        """
        return self.status_code in (204, 205, 304)

    def is_informational(self) -> bool:
        """
        Checks if the response is an informational response (1xx status codes).
        """
        return 100 <= self.status_code < 200

    def is_successful(self) -> bool:
        """
        Checks if the response is a successful response (2xx status codes).
        """
        return 200 <= self.status_code < 300

    def is_redirection(self) -> bool:
        """
        Checks if the response is a redirect response (3xx status codes).
        """
        return 300 <= self.status_code < 400

    def is_client_error(self) -> bool:
        """
        Checks if the response is a client error response (4xx status codes).
        """
        return 400 <= self.status_code < 500

    def is_server_error(self) -> bool:
        """
        Checks if the response is a server error response (5xx status codes).
        """
        return 500 <= self.status_code < 600

    def is_ok(self) -> bool:
        """
        Checks if the response is an OK response (200 status code).
        """
        return self.status_code == 200

    def is_rendered(self) -> bool:
        """
        Checks if the response has been rendered.
        """
        return self._rendered

    async def start_response(self, send: Send) -> None:
        """
        Starts the response by sending the status line and headers.
        This method should be called before sending the body.
        """
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.encode_headers(),
            }
        )

    async def send_body(self, send: Send, receive: Receive) -> None:
        """
        Sends the response body.
        This method should be called after starting the response.
        """
        body = await self.render()

        event = {
            "type": "http.response.body",
            "body": body if body is not None else b"",
            "more_body": False,
        }

        await send(event)

    async def run_deferred(self) -> None:
        """
        Runs all deferred functions after the response has been sent.
        """
        for func in self._deferred:
            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                await run_in_threadpool(func)
