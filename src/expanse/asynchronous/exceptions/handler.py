import logging

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from typing import Self

from cleo.io.outputs.output import Output
from crashtest.inspector import Inspector
from pydantic import ValidationError

from expanse.asynchronous.container.container import Container
from expanse.asynchronous.contracts.debug.exception_handler import (
    ExceptionHandler as ExceptionHandlerContract,
)
from expanse.asynchronous.contracts.debug.exception_renderer import ExceptionRenderer
from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response
from expanse.common.configuration.config import Config
from expanse.common.core.http.exceptions import HTTPException


logger = logging.getLogger(__name__)


class ExceptionHandler(ExceptionHandlerContract):
    def __init__(self, container: Container) -> None:
        self._container = container

        self._dont_report: set[type[Exception]] = {HTTPException, ValidationError}
        self._raise_unhandled_exceptions: bool = False

    async def report(self, e: Exception) -> None:
        if not await self.should_report(e):
            return

        await self._report_exception(e)

    async def _report_exception(self, e: Exception) -> None:
        # TODO: Better logging handling
        if self._raise_unhandled_exceptions:
            raise e

    async def should_report(self, e: Exception) -> bool:
        return not any(isinstance(e, klass) for klass in self._dont_report)

    def ignore(self, exception_class: type[Exception]) -> Self:
        self._dont_report.add(exception_class)

        return self

    def stop_ignoring(self, exception_class: type[Exception]) -> Self:
        if exception_class in self._dont_report:
            self._dont_report.remove(exception_class)

        return self

    async def render(self, request: Request, e: Exception) -> Response:
        if isinstance(e, ValidationError):
            return await self._render_validation_exception(e, request)

        return await self._render_exception_response(request, e)

    async def render_for_console(self, output: Output, e: Exception) -> None:
        from cleo.ui.exception_trace import ExceptionTrace

        trace = ExceptionTrace(e)

        trace.render(output)

    async def _render_exception_response(
        self, request: Request, e: Exception
    ) -> Response:
        if request.expects_json():
            return await self._render_json_response(request, e)

        return await self._render_response(request, e)

    async def _render_json_response(self, request: Request, e: Exception) -> Response:
        from expanse.asynchronous.routing.redirect import Redirect
        from expanse.asynchronous.routing.responder import Responder
        from expanse.asynchronous.routing.router import Router
        from expanse.asynchronous.view.view_factory import ViewFactory

        responder = Responder(
            await self._container.make(ViewFactory),
            Redirect(await self._container.make(Router), request),
        )

        return await responder.json(
            await self._convert_exception_to_dict(e),
            status_code=e.status_code if isinstance(e, HTTPException) else 500,
            indent=2,
            headers=e.headers if isinstance(e, HTTPException) else {},
        )

    async def _render_response(self, request: Request, e: Exception) -> Response:
        config = await self._container.make(Config)
        if not isinstance(e, HTTPException) and config.get("app.debug"):
            if self._container.has(ExceptionRenderer):
                return Response(
                    await (await self._container.make(ExceptionRenderer)).render(e),
                    status_code=500,
                    content_type="text/html",
                )

            return Response(
                await self._render_exception_content(e),
                status_code=500,
                content_type="text/plain",
            )

        if not isinstance(e, HTTPException):
            e = HTTPException(500, str(e))

        return await self._render_http_exception(e)

    async def _render_http_exception(self, e: HTTPException) -> Response:
        await self._register_error_paths()

        if view := (await self._get_http_exception_view(e)):
            from expanse.asynchronous.view.view_factory import ViewFactory

            factory = await self._container.make(ViewFactory)

            response = await factory.render(
                await factory.make(view, {"exception": e}, status_code=e.status_code)
            )

            return response

        return Response(
            await self._render_exception_content(e),
            status_code=e.status_code,
            content_type="text/plain",
            headers=e.headers,
        )

    async def _render_validation_exception(
        self, e: ValidationError, request: Request
    ) -> Response:
        if request.expects_json() or request.is_json():
            content = {"code": "validation_error", "detail": []}

            assert isinstance(content["detail"], list)

            for error in e.errors():
                content["detail"].append(
                    {
                        "loc": error["loc"],
                        "message": error["msg"],
                        "type": error["type"],
                    }
                )

            from expanse.asynchronous.routing.redirect import Redirect
            from expanse.asynchronous.routing.responder import Responder
            from expanse.asynchronous.routing.router import Router
            from expanse.asynchronous.view.view_factory import ViewFactory

            responder = Responder(
                await self._container.make(ViewFactory),
                Redirect(await self._container.make(Router), request),
            )

            return await responder.json(content, status_code=422)

        http_exception = HTTPException(422, str(e))

        return await self._render_http_exception(http_exception)

    async def _get_http_exception_view(self, e: HTTPException) -> str | None:
        view = f"errors/{e.status_code}"

        from expanse.asynchronous.view.view_factory import ViewFactory

        factory = await self._container.make(ViewFactory)

        if not factory.exists(view):
            return None

        return view

    async def _register_error_paths(self) -> None:
        import expanse

        from expanse.asynchronous.view.view_finder import ViewFinder

        (await self._container.make(ViewFinder)).add_paths(
            [Path(expanse.__file__).parent.joinpath("common/exceptions/views")]
        )

    async def _render_exception_content(self, e: Exception) -> str:
        config = await self._container.make(Config)
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

    async def _convert_exception_to_dict(self, e: Exception) -> dict[str, Any]:
        debug = (await self._container.make(Config)).get("app.debug", False)
        if debug:
            inspector = Inspector(e)

            return {
                "message": inspector.exception_message,
                "exception": inspector.exception_name,
                "file": inspector.frames[-1].filename,
                "line": inspector.frames[-1].lineno,
            }

        return {"message": e.detail if isinstance(e, HTTPException) else "Server error"}

    def dont_report(self, *e: type[Exception]) -> Self:
        self._dont_report |= set(e)

        return self

    @contextmanager
    def raise_unhandled_exceptions(
        self, raise_exceptions: bool = True
    ) -> Generator[None, None, None]:
        original_value = self._raise_unhandled_exceptions
        self._raise_unhandled_exceptions = raise_exceptions

        yield

        self._raise_unhandled_exceptions = original_value
