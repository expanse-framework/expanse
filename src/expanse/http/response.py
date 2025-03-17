from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from typing import Self

from baize.asgi.responses import PlainTextResponse
from baize.asgi.responses import Response as BaizeResponse
from baize.asgi.responses import SmallResponse as BaizeSmallResponse

from expanse.http.cookie import Cookie
from expanse.http.cookie import SameSite
from expanse.http.request import Request


if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import MutableMapping

    from expanse.types import Receive
    from expanse.types import Scope
    from expanse.types import Send


class Response:
    def __init__(
        self,
        content: bytes | str | None = None,
        status_code: int = 200,
        headers: MutableMapping[str, str] | None = None,
        content_type: str | None = None,
        *,
        response: BaizeResponse | None = None,
    ) -> None:
        if response is None:
            response = PlainTextResponse(
                content=content or "",
                status_code=status_code,
                headers=headers,
                media_type=content_type,
            )

        self._response = response
        self._status_code = response.status_code
        self._headers = response.headers
        self._cookies: dict[str, Cookie] = {}

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def headers(self) -> MutableMapping[str, str]:
        return self._response.headers

    @property
    def cookies(self) -> dict[str, Cookie]:
        return self._cookies

    @property
    def content_type(self) -> str | None:
        if isinstance(self._response, BaizeSmallResponse):
            return self._response.media_type

        if hasattr(self._response, "content_type"):
            return self._response.content_type

        if "Content-Type" in self._response.headers:
            return self._response.headers["Content-Type"]

        return None

    @property
    def charset(self) -> str | None:
        if isinstance(self._response, BaizeSmallResponse):
            return self._response.charset

        return None

    def with_status(self, status_code: int) -> Self:
        self._response.status_code = status_code

        return self

    def with_header(self, key: str, value: str) -> Self:
        self._response.headers[key] = value

        return self

    def with_headers(self, headers: Mapping[str, str]) -> Self:
        self._response.headers.update(headers)

        return self

    def set_cookie(
        self,
        name: str,
        value: str | None = None,
        expires: int | datetime = 0,
        domain: str | None = None,
        path: str | None = None,
        secure: bool = False,
        http_only: bool = False,
        same_site: SameSite = SameSite.LAX,
        partitioned: bool = False,
    ):
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
        self._cookies[name] = Cookie(
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

    async def prepare(self, request: Request) -> None:
        is_request_secure = request.is_secure()

        for name, cookie in self._cookies.items():
            if is_request_secure:
                cookie.set_secure_default(is_request_secure)

            self._response.set_cookie(
                name,
                cookie.value,
                expires=cookie.expires,
                path=cookie.path,
                domain=cookie.domain,
                secure=cookie.is_secure(),
                httponly=cookie.is_http_only(),
                samesite=cookie.same_site,
            )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        return await self._response(scope=scope, receive=receive, send=send)
