from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from typing import Literal
from typing import Self

from baize.asgi.responses import PlainTextResponse
from baize.asgi.responses import Response as BaizeResponse
from baize.asgi.responses import SmallResponse as BaizeSmallResponse
from baize.datastructures import Cookie


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
        self._cookies = response.cookies

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def headers(self) -> MutableMapping[str, str]:
        return self._response.headers

    @property
    def cookies(self) -> list[Cookie]:
        return self._response.cookies

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
        key: str,
        value: str = "",
        max_age: int = -1,
        expires: int | datetime | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Literal["strict", "lax", "none"] = "lax",
    ) -> None:
        self._response.cookies.append(
            Cookie(
                key,
                value,
                expires=self._compute_expires(expires),
                max_age=max_age,
                path=path,
                domain=domain,
                secure=secure,
                httponly=httponly,
                samesite=samesite,
            )
        )

    def delete_cookie(
        self,
        key: str,
        value: str = "",
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Literal["strict", "lax", "none"] = "lax",
    ) -> None:
        self.set_cookie(
            key,
            value=value,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
        )

    def _compute_expires(self, expires: int | datetime | None) -> datetime | None:
        if expires is None:
            return None

        if isinstance(expires, datetime):
            return expires

        return datetime.fromtimestamp(expires)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        return await self._response(scope=scope, receive=receive, send=send)
