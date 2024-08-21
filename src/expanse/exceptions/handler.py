from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from typing import Self

from cleo.io.outputs.output import Output
from crashtest.inspector import Inspector
from pydantic import ValidationError

from expanse.common.configuration.config import Config
from expanse.common.core.http.exceptions import HTTPException
from expanse.container.container import Container
from expanse.contracts.debug.exception_handler import (
    ExceptionHandler as ExceptionHandlerContract,
)
from expanse.contracts.debug.exception_renderer import ExceptionRenderer
from expanse.http.request import Request
from expanse.http.response import Response


class ExceptionHandler(ExceptionHandlerContract):
    def __init__(self, container: Container) -> None:
        self._container = container

        self._dont_report: set[type[Exception]] = {HTTPException, ValidationError}
        self._raise_unhandled_exceptions: bool = False

    def report(self, e: Exception) -> None:
        if not self.should_report(e):
            return

        self._report_exception(e)

    def _report_exception(self, e: Exception) -> None:
        if self._raise_unhandled_exceptions:
            raise e

    def should_report(self, e: Exception) -> bool:
        return not any(isinstance(e, klass) for klass in self._dont_report)

    def ignore(self, exception_class: type[Exception]) -> Self:
        self._dont_report.add(exception_class)

        return self

    def stop_ignoring(self, exception_class: type[Exception]) -> Self:
        if exception_class in self._dont_report:
            self._dont_report.remove(exception_class)

        return self

    def render(self, request: Request, e: Exception) -> Response:
        if isinstance(e, ValidationError):
            return self._render_validation_exception(e, request)

        return self._render_exception_response(request, e)

    def render_for_console(self, output: Output, e: Exception) -> None:
        from cleo.ui.exception_trace import ExceptionTrace

        trace = ExceptionTrace(e)

        trace.render(output)

    def _render_exception_response(self, request: Request, e: Exception) -> Response:
        if request.expects_json():
            return self._render_json_response(request, e)

        return self._render_response(request, e)

    def _render_json_response(self, request: Request, e: Exception) -> Response:
        from expanse.routing.responder import Responder

        if self._container.has(Responder):
            responder = self._container.make(Responder)
        else:
            from expanse.routing.redirect import Redirect
            from expanse.routing.router import Router
            from expanse.view.view_factory import ViewFactory

            responder = Responder(
                self._container.make(ViewFactory),
                Redirect(self._container.make(Router), request),
            )

        return responder.json(
            self._convert_exception_to_dict(e),
            status_code=e.status_code if isinstance(e, HTTPException) else 500,
            indent=2,
            headers=e.headers if isinstance(e, HTTPException) else None,
        )

    def _render_response(self, request: Request, e: Exception) -> Response:
        if not isinstance(e, HTTPException) and self._container.make(Config).get(
            "app.debug"
        ):
            if self._container.has(ExceptionRenderer):
                return Response(
                    self._container.make(ExceptionRenderer).render(e),
                    status_code=500,
                    content_type="text/html",
                )

            return Response(
                self._render_exception_content(e),
                status_code=500,
                content_type="text/plain",
            )

        if not isinstance(e, HTTPException):
            e = HTTPException(500, str(e))

        return self._render_http_exception(e)

    def _render_http_exception(self, e: HTTPException) -> Response:
        self._register_error_paths()

        if view := self._get_http_exception_view(e):
            from expanse.view.view_factory import ViewFactory

            factory = self._container.make(ViewFactory)

            response = factory.render(
                factory.make(view, {"exception": e}, status_code=e.status_code)
            )

            return response

        return Response(
            self._render_exception_content(e),
            status_code=e.status_code,
            content_type="text/plain",
            headers=e.headers,
        )

    def _render_validation_exception(
        self, e: ValidationError, request: Request
    ) -> Response:
        if request.expects_json() or request.is_json():
            content: dict[str, Any] = {"code": "validation_error"}
            details: list[dict[str, Any]] = []

            for error in e.errors():
                details.append(
                    {
                        "loc": error["loc"],
                        "message": error["msg"],
                        "type": error["type"],
                    }
                )

            content["detail"] = details

            from expanse.routing.redirect import Redirect
            from expanse.routing.responder import Responder
            from expanse.routing.router import Router
            from expanse.view.view_factory import ViewFactory

            responder = Responder(
                self._container.make(ViewFactory),
                Redirect(self._container.make(Router), request),
            )

            return responder.json(content, status_code=422)

        http_exception = HTTPException(422, str(e))

        return self._render_http_exception(http_exception)

    def _get_http_exception_view(self, e: HTTPException) -> str | None:
        view = f"errors/{e.status_code}"

        from expanse.view.view_factory import ViewFactory

        factory = self._container.make(ViewFactory)

        if not factory.exists(view):
            return None

        return view

    def _render_exception_content(self, e: Exception) -> str:
        config = self._container.make(Config)
        if config.get("app.debug", False):
            inspector = Inspector(e)

            message = [f"{inspector.exception_name}: {inspector.exception_message}"]

            if inspector.frames:
                message.extend(
                    [
                        f"in {inspector.frames[-1].filename}",
                        f"at line {inspector.frames[-1].lineno}",
                    ]
                )

            return " ".join(message)

        return e.detail if isinstance(e, HTTPException) else "Server Error"

    def _convert_exception_to_dict(self, e: Exception) -> dict[str, Any]:
        debug = self._container.make(Config).get("app.debug", False)
        if debug:
            inspector = Inspector(e)

            return {
                "message": inspector.exception_message,
                "exception": inspector.exception_name,
                "file": inspector.frames[-1].filename,
                "line": inspector.frames[-1].lineno,
            }

        return {"message": e.detail if isinstance(e, HTTPException) else "Server error"}

    def _register_error_paths(self) -> None:
        import expanse

        from expanse.view.view_finder import ViewFinder

        self._container.make(ViewFinder).add_paths(
            [Path(expanse.__file__).parent.joinpath("common/exceptions/views")]
        )

    def dont_report(self, *e: type[Exception]) -> Self:
        self._dont_report |= set(e)

        return self

    @contextmanager
    def raise_unhandled_exceptions(
        self, raise_exceptions: bool = True
    ) -> Generator[None]:
        original_value = self._raise_unhandled_exceptions
        self._raise_unhandled_exceptions = raise_exceptions

        yield

        self._raise_unhandled_exceptions = original_value
