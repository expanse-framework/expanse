from collections.abc import Awaitable
from collections.abc import Callable
from functools import wraps

from expanse.asynchronous.container.container import Container
from expanse.asynchronous.core.http.middleware.middleware import Middleware
from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.types.http.middleware import RequestHandler
from expanse.asynchronous.types.routing import Endpoint


class MiddlewareStack:
    def __init__(
        self, container: Container, middlewares: list[type[Middleware]] | None = None
    ) -> None:
        self._container = container
        self._middlewares: list[type[Middleware]] = middlewares or []

    async def handle(self, endpoint: Endpoint, *parameters) -> Response:
        stack = await self._build_stack(endpoint, *parameters)
        return await stack(await self._container.make(Request))

    async def _build_stack(self, endpoint: Endpoint, *parameters) -> RequestHandler:
        async def endpoint_call(_: Request) -> Response:
            return await self._container.call(endpoint, *parameters)

        stack = endpoint_call

        for middleware_class in reversed(self._middlewares):
            middleware = await self._container.make(middleware_class)
            stack = await self._wrap(middleware)(stack)

        return stack

    def _wrap(
        self, middleware: Middleware
    ) -> Callable[[RequestHandler], Awaitable[RequestHandler]]:
        @wraps(middleware.handle)
        async def decorator(next_call: RequestHandler) -> RequestHandler:
            @wraps(next_call)
            async def view(request: Request) -> Response:
                return await self._container.call(middleware.handle, next_call)

            return view

        return decorator
