from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Literal
from typing import NoReturn
from typing import Self

from baize.asgi.responses import FileResponse
from baize.asgi.responses import JSONResponse
from baize.asgi.responses import PlainTextResponse
from baize.asgi.responses import Response as BaizeResponse
from baize.asgi.responses import SmallResponse as BaizeSmallResponse

from expanse.common.core.http.exceptions import HTTPException


if TYPE_CHECKING:
    from collections.abc import Mapping
    from os import PathLike

    from expanse.asynchronous.types import Receive
    from expanse.asynchronous.types import Scope
    from expanse.asynchronous.types import Send


class Response:
    def __init__(
        self,
        content: bytes | str | None = None,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        *,
        response: BaizeResponse | None = None,
    ) -> None:
        if response is None:
            response = PlainTextResponse(
                content=content or "",
                status_code=status_code,
                headers=headers,
                media_type=media_type,
            )

        self.response = response
        self.status_code = response.status_code
        self.headers = response.headers
        self.cookies = response.cookies

        if isinstance(response, BaizeSmallResponse):
            self.media_type = response.media_type
            self.charset = response.charset
        else:
            self.media_type = None
            self.charset = None

    @classmethod
    def json(
        cls,
        content: Any = None,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> Self:
        return cls(
            response=JSONResponse(
                content, status_code=status_code, headers=headers, **kwargs
            )
        )

    @classmethod
    def html(
        cls,
        content: Any = "",
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
    ) -> Self:
        return cls(
            response=PlainTextResponse(
                content,
                status_code=status_code,
                headers=headers,
                media_type="text/html",
            )
        )

    @classmethod
    def text(
        cls,
        content: Any = "",
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
    ) -> Self:
        return cls(
            response=PlainTextResponse(
                content, status_code=status_code, headers=headers
            )
        )

    @classmethod
    def file(
        cls,
        path: str | PathLike[str],
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        filename: str | None = None,
    ) -> Self:
        return cls(
            response=FileResponse(
                path,
                headers=headers,
                content_type=media_type,
                download_name=filename,
            )
        )

    @classmethod
    def abort(
        cls,
        status_code: int,
        message: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> NoReturn:
        raise HTTPException(status_code, detail=message, headers=headers)

    def set_cookie(
        self,
        key: str,
        value: str = "",
        max_age: int = -1,
        expires: int | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Literal["strict", "lax", "none"] = "lax",
    ) -> None:
        self.response.set_cookie(
            key,
            value=value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
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

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        return await self.response(scope=scope, receive=receive, send=send)
