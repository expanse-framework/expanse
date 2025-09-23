from functools import partial
from typing import Self

from expanse.contracts.routing.router import Router
from expanse.core.application import Application
from expanse.core.http.middleware.middleware import Middleware
from expanse.core.http.middleware.middleware_group import MiddlewareGroup
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.routing.pipeline import Pipeline
from expanse.types import Receive
from expanse.types import Scope
from expanse.types import Send


class Portal:
    """
    The HTTP portal is the layer between the ASGI spec/world and Expanse internal
    architecture.
    """

    def __init__(self, app: Application, router: Router) -> None:
        self._app = app
        self._router = router
        self._middleware: list[type[Middleware]] = []
        self._middleware_groups: dict[str, MiddlewareGroup] = {}

    async def handle(self, request: Request) -> Response:
        async with self._app.container.create_scoped_container() as container:
            container.instance(Request, request)

            try:
                response = await (
                    Pipeline(container)
                    .use(
                        [
                            (await container.get(middleware)).handle
                            for middleware in self._middleware
                        ]
                    )
                    .send(request)
                    .to(partial(self._router.handle, container))
                )

                await response.prepare(request, container)
            except Exception as e:
                from expanse.contracts.debug.exception_handler import ExceptionHandler

                if not self._app.container.has(ExceptionHandler):
                    raise e

                exception_handler = await self._app.container.get(ExceptionHandler)

                await exception_handler.report(e)

                response = await exception_handler.render(request, e)

                await response.prepare(request, container)

            return response

    def set_middleware(self, middleware: list[type[Middleware]]) -> Self:
        self._middleware = middleware

        self._configure_router()

        return self

    def prepend_middleware(self, middleware: type[Middleware]) -> Self:
        if middleware not in self._middleware:
            self._middleware.insert(0, middleware)

        self._configure_router()

        return self

    def append_middleware(self, middleware: type[Middleware]) -> Self:
        if middleware not in self._middleware:
            self._middleware.append(middleware)

        self._configure_router()

        return self

    def set_middleware_groups(self, groups: dict[str, MiddlewareGroup]) -> Self:
        self._middleware_groups = groups

        self._configure_router()

        return self

    def _configure_router(self) -> None:
        for name, group in self._middleware_groups.items():
            self._router.middleware_group(name, group.middleware)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive, send)

        response = await self.handle(request)

        await response.start_response(send)
        await response.send_body(send, receive)
        await response.run_deferred()
