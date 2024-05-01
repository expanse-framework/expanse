from typing import Any
from typing import Self

from cleo.io.outputs.output import Output
from crashtest.inspector import Inspector

from expanse.common.configuration.config import Config
from expanse.common.foundation.http.exceptions import HTTPException
from expanse.container.container import Container
from expanse.contracts.debug.exception_handler import (
    ExceptionHandler as ExceptionHandlerContract,
)
from expanse.http.request import Request
from expanse.http.response import Response


class ExceptionHandler(ExceptionHandlerContract):
    def __init__(self, container: Container) -> None:
        self._container = container

        self._dont_report: set[type[Exception]] = {HTTPException}

    def report(self, e: Exception) -> None:
        if not self.should_report(e):
            return

        self._report_exception(e)

    def _report_exception(self, e: Exception) -> None:
        raise e

    def should_report(self, e: Exception) -> bool:
        return e.__class__ not in self._dont_report

    def ignore(self, exception_class: type[Exception]) -> Self:
        self._dont_report.add(exception_class)

        return self

    def stop_ignoring(self, exception_class: type[Exception]) -> Self:
        if exception_class in self._dont_report:
            self._dont_report.remove(exception_class)

        return self

    def render(self, request: Request, e: Exception) -> Response:
        return self._render_exception_response(request, e)

    def render_for_console(self, output: Output, e: Exception) -> None:
        from cleo.ui.exception_trace import ExceptionTrace

        trace = ExceptionTrace(e)

        trace.render(output)

    def _render_exception_response(self, request: Request, e: Exception) -> Response:
        if request.expects_json():
            return self._prepare_json_response(request, e)

        return self._prepare_response(request, e)

    def _prepare_json_response(self, request: Request, e: Exception) -> Response:
        return Response.json(
            self._convert_exception_to_dict(e),
            status_code=e.status_code if isinstance(e, HTTPException) else 500,
            indent=2,
        )

    def _prepare_response(self, request: Request, e: Exception) -> Response:
        return Response.text(
            self._render_exception_content(e),
            status_code=e.status_code if isinstance(e, HTTPException) else 500,
        )

    def _render_exception_content(self, e: Exception) -> str:
        config = self._container.make(Config)
        if config.get("app.debug", False):
            inspector = Inspector(e)

            return (
                f"{inspector.exception_name}: {inspector.exception_message} "
                f"in {inspector.frames[-1].filename} "
                f"at line {inspector.frames[-1].lineno}"
            )

        return e.detail if isinstance(e, HTTPException) else "Server Error"

    def _convert_exception_to_dict(self, e: Exception) -> dict[str, Any]:
        debug = self._container.make(Config).get("app.debug", False)
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
