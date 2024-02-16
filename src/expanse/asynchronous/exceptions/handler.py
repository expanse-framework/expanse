from typing import Any
from typing import Self

from crashtest.inspector import Inspector

from expanse.asynchronous.container.container import Container
from expanse.asynchronous.contracts.debug.exception_handler import (
    ExceptionHandler as ExceptionHandlerContract,
)
from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response
from expanse.common.configuration.config import Config
from expanse.common.foundation.http.exceptions import HTTPException


class ExceptionHandler(ExceptionHandlerContract):
    def __init__(self, container: Container) -> None:
        self._container = container

        self._dont_report: set[type[Exception]] = {HTTPException}

    async def report(self, e: Exception) -> None:
        if not await self.should_report(e):
            return

        await self._report_exception(e)

    async def _report_exception(self, e: Exception) -> None:
        raise e

    async def should_report(self, e: Exception) -> bool:
        return e.__class__ not in self._dont_report

    def ignore(self, exception_class: type[Exception]) -> Self:
        self._dont_report.add(exception_class)

        return self

    def stop_ignoring(self, exception_class: type[Exception]) -> Self:
        if exception_class in self._dont_report:
            self._dont_report.remove(exception_class)

        return self

    async def render(self, request: Request, e: Exception) -> Response:
        return await self._render_exception_response(request, e)

    async def _render_exception_response(
        self, request: Request, e: Exception
    ) -> Response:
        if request.expects_json():
            return await self._prepare_json_response(request, e)

        return await self._prepare_response(request, e)

    async def _prepare_json_response(self, request: Request, e: Exception) -> Response:
        return Response.json(
            self._convert_exception_to_dict(e),
            status_code=e.status_code if isinstance(e, HTTPException) else 500,
            indent=2,
        )

    async def _prepare_response(self, request: Request, e: Exception) -> Response:
        return Response.text(
            e.detail if isinstance(e, HTTPException) else "Server Error",
            status_code=e.status_code if isinstance(e, HTTPException) else 500,
        )

    async def _convert_exception_to_dict(self, e: Exception) -> dict[str, Any]:
        debug = (await self._container.make(Config)).get("app.debug", False)
        if debug:
            inspector = Inspector(e)

            return {
                "message": inspector.exception_message,
                "exception": inspector.exception_name,
                "file": inspector.frames[0].filename,
                "line": inspector.frames[0].lineno,
            }

        return {"message": e.detail if isinstance(e, HTTPException) else "Server error"}

    def dont_report(self, *e: type[Exception]) -> Self:
        self._dont_report |= set(e)

        return self
