from collections.abc import Callable
from functools import wraps

from expanse.container.container import Container
from expanse.core.http.middleware.middleware import Middleware
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.types.http.middleware import RequestHandler
from expanse.types.routing import Endpoint


class MiddlewareStack:
    def __init__(
        self, container: Container, middlewares: list[type[Middleware]] | None = None
    ) -> None:
        self._container = container
        self._middlewares = middlewares or []

    def handle(self, endpoint: Endpoint, *parameters) -> Response:
        return self._build_stack(endpoint, *parameters)(self._container.make(Request))

    def _build_stack(self, endpoint: Endpoint, *parameters) -> RequestHandler:
        def endpoint_call(_: Request) -> Response:
            return self._container.call(endpoint, *parameters)

        stack = endpoint_call

        for middleware_class in reversed(self._middlewares):
            middleware = self._container.make(middleware_class)
            stack = self._wrap(middleware)(stack)

        return stack

    def _wrap(
        self, middleware: Middleware
    ) -> Callable[[RequestHandler], RequestHandler]:
        @wraps(middleware.handle)
        def decorator(next_call: RequestHandler) -> Callable[[Request], Response]:
            @wraps(next_call)
            def view(request: Request) -> Response:
                return self._container.call(middleware.handle, next_call)

            return view

        return decorator
