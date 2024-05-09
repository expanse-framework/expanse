from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Literal
from typing import NoReturn
from typing import Self

from baize.wsgi.responses import FileResponse
from baize.wsgi.responses import JSONResponse
from baize.wsgi.responses import PlainTextResponse
from baize.wsgi.responses import Response as BaizeResponse
from baize.wsgi.responses import SmallResponse as BaizeSmallResponse

from expanse.common.core.http.exceptions import HTTPException


if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from os import PathLike

    from expanse.types import Environ
    from expanse.types import StartResponse


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
    def text(
        cls,
        content: Any = "",
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str = "text/plain",
    ) -> Self:
        return cls(
            response=PlainTextResponse(
                content, status_code=status_code, headers=headers, media_type=media_type
            )
        )

    @classmethod
    def html(
        cls,
        content: Any = "",
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
    ) -> Self:
        return cls.text(
            content,
            status_code=status_code,
            headers=headers,
            media_type="text/html",
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
                str(path),
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

    def __call__(
        self, environ: Environ, start_response: StartResponse
    ) -> Iterable[bytes]:
        return self.response(environ, start_response)
