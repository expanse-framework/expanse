from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import NoReturn

from baize.asgi import JSONResponse

from expanse.core.helpers import _get_container
from expanse.core.http.exceptions import HTTPException
from expanse.http.response import Response


if TYPE_CHECKING:
    from collections.abc import MutableMapping
    from os import PathLike

    from expanse.http.redirect import Redirect
    from expanse.http.responder import AsyncResponder


def abort(
    status_code: int,
    message: str | None = None,
    headers: MutableMapping[str, str] | None = None,
) -> NoReturn:
    raise HTTPException(status_code, message, headers)


def json(
    content: Any = "",
    status_code: int = 200,
    headers: MutableMapping[str, Any] | None = None,
    **kwargs: Any,
) -> Response:
    return Response(
        response=JSONResponse(
            content, status_code=status_code, headers=headers, **kwargs
        )
    )


def file_(
    path: str | PathLike[str],
    headers: MutableMapping[str, str] | None = None,
    media_type: str | None = None,
    filename: str | None = None,
    chunk_size: int = 4096 * 64,
) -> Response:
    from baize.asgi import FileResponse

    return Response(
        response=FileResponse(
            str(path),
            headers=headers,
            content_type=media_type,
            download_name=filename,
            chunk_size=chunk_size,
        )
    )


async def redirect() -> Redirect:
    return (await respond()).redirect()


async def respond() -> AsyncResponder:
    container = _get_container()

    from expanse.http.responder import AsyncResponder

    return await container.get(AsyncResponder)


async def response(
    content: str = "",
    status_code: int = 200,
    headers: MutableMapping[str, Any] | None = None,
) -> Response:
    return (await respond()).html(content, status_code, headers)


async def view(
    view: str,
    data: MutableMapping[str, Any] | None = None,
    status_code: int = 200,
    headers: MutableMapping[str, Any] | None = None,
) -> Response:
    return await (await respond()).view(view, data, status_code, headers)
