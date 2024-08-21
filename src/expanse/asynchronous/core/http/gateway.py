from functools import partial
from typing import Self

from expanse.asynchronous.core.application import Application
from expanse.asynchronous.core.http.middleware.middleware import Middleware
from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.pipeline import Pipeline
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.types import Receive
from expanse.asynchronous.types import Scope
from expanse.asynchronous.types import Send


class Gateway:
    """
    The gateway is the layer between the ASGI spec/world and Expanse internal
    architecture.
    """

    def __init__(self, app: Application, router: Router) -> None:
        self._app = app
        self._router = router
        self._middleware: list[type[Middleware]] = []
        self._group_middleware: dict[str, list[type[Middleware]]] = {}

    async def handle(self, request: Request) -> Response:
        async with self._app.container.create_scoped_container() as container:
            container.instance(Request, request)

            return await (
                Pipeline(container)
                .use(
                    [
                        (await container.make(middleware)).handle
                        for middleware in self._middleware
                    ]
                )
                .send(request)
                .to(partial(self._router.handle, container))
            )

    def set_middleware(self, middleware: list[type[Middleware]]) -> Self:
        self._middleware = middleware

        return self

    def prepend_middleware(self, middleware: type[Middleware]) -> Self:
        if middleware not in self._middleware:
            self._middleware.insert(0, middleware)

        return self

    def append_middleware(self, middleware: type[Middleware]) -> Self:
        if middleware not in self._middleware:
            self._middleware.append(middleware)

        return self

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive, send)

        response = await self.handle(request)

        return await self._prepare_response(response, scope, receive, send)

    async def _prepare_response(
        self, response: Response, scope: Scope, receive: Receive, send: Send
    ) -> None:
        return await response(scope, receive, send)
