from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Literal
from typing import NoReturn

import msgspec.json

from expanse.core.http.exceptions import HTTPException
from expanse.http.response import Response
from expanse.http.responses.redirect import RedirectResponse


if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import MutableMapping
    from os import PathLike

    from expanse.http.responses.view import ViewResponse


def abort(
    status_code: int,
    message: str | None = None,
    *,
    headers: MutableMapping[str, str] | None = None,
) -> NoReturn:
    raise HTTPException(status_code, message, headers)


def text(
    content: str = "",
    status_code: int = 200,
    *,
    headers: MutableMapping[str, Any] | None = None,
    content_type: str = "text/plain",
    encoding: str = "utf-8",
) -> Response:
    return Response(
        content,
        status_code=status_code,
        content_type=content_type,
        encoding=encoding,
        headers=headers,
    )


def html(
    content: str = "",
    status_code: int = 200,
    *,
    headers: MutableMapping[str, Any] | None = None,
    encoding: str = "utf-8",
) -> Response:
    return text(
        content,
        status_code=status_code,
        headers=headers,
        content_type="text/html",
        encoding=encoding,
    )


def json(
    content: Any = "",
    status_code: int = 200,
    *,
    headers: Mapping[str, Any] | None = None,
) -> Response:
    return Response(
        msgspec.json.encode(content),
        status_code=status_code,
        content_type="application/json",
        headers=headers,
    )


def file_(
    path: str | PathLike[str],
    *,
    headers: Mapping[str, str] | None = None,
    media_type: str | None = None,
    filename: str | None = None,
    content_disposition: Literal["attachment", "inline"] = "inline",
    chunk_size: int = 1024 * 1024,
) -> Response:
    from expanse.http.responses.file import FileResponse

    return FileResponse(
        path,
        content_type=media_type,
        headers=headers,
        filename=filename,
        content_disposition=content_disposition,
        chunk_size=chunk_size,
    )


def download(
    path: str | PathLike[str],
    *,
    headers: Mapping[str, str] | None = None,
    media_type: str | None = None,
    filename: str | None = None,
    chunk_size: int = 1024 * 1024,
) -> Response:
    from expanse.http.responses.file import FileResponse

    return FileResponse(
        path,
        content_type=media_type,
        headers=headers,
        filename=filename,
        content_disposition="attachment",
        chunk_size=chunk_size,
    )


def redirect(
    status_code: int = 302, *, headers: Mapping[str, Any] | None = None
) -> RedirectResponse:
    return RedirectResponse(status_code, headers=headers)


def view(
    view: str,
    *,
    data: Mapping[str, Any] | None = None,
    status_code: int = 200,
    headers: Mapping[str, Any] | None = None,
    content_type: str = "text/html",
) -> ViewResponse:
    from expanse.http.responses.view import ViewResponse

    return ViewResponse(
        view,
        data=data,
        status_code=status_code,
        headers=headers,
        content_type=content_type,
    )


__all__ = ["abort", "file_", "json", "redirect", "view"]
