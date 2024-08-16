from collections.abc import Mapping
from collections.abc import MutableMapping
from os import PathLike
from typing import Any
from typing import NoReturn

from baize.wsgi import FileResponse
from baize.wsgi import JSONResponse
from baize.wsgi import PlainTextResponse

from expanse.common.core.http.exceptions import HTTPException
from expanse.http.response import Response
from expanse.routing.redirect import Redirect
from expanse.view.view_factory import ViewFactory


class Responder:
    def __init__(self, view: ViewFactory, redirect: Redirect) -> None:
        self._view = view
        self._redirect = redirect

    def redirect(self) -> Redirect:
        return self._redirect

    def text(
        self,
        content: str = "",
        status_code: int = 200,
        headers: Mapping[str, Any] | None = None,
        media_type: str = "text/plain",
    ) -> Response:
        return Response(
            response=PlainTextResponse(
                content, status_code=status_code, headers=headers, media_type=media_type
            )
        )

    def html(
        self,
        content: str = "",
        status_code: int = 200,
        headers: Mapping[str, Any] | None = None,
    ) -> Response:
        return self.text(
            content, status_code=status_code, headers=headers, media_type="text/html"
        )

    def json(
        self,
        content: Any = "",
        status_code: int = 200,
        headers: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> Response:
        return Response(
            response=JSONResponse(
                content, status_code=status_code, headers=headers, **kwargs
            )
        )

    def file(
        self,
        path: str | PathLike[str],
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        filename: str | None = None,
        chunk_size: int = 4096 * 64,
    ) -> Response:
        return Response(
            response=FileResponse(
                str(path),
                headers=headers,
                content_type=media_type,
                download_name=filename,
                chunk_size=chunk_size,
            )
        )

    def view(
        self,
        view: str,
        data: Mapping[str, Any] | None = None,
        status_code: int = 200,
        headers: MutableMapping[str, Any] | None = None,
    ) -> Response:
        return self._view.render(self._view.make(view, data, status_code, headers))

    def abort(
        self,
        status_code: int,
        message: str | None = None,
        headers: MutableMapping[str, str] | None = None,
    ) -> NoReturn:
        raise HTTPException(status_code, detail=message, headers=headers)
