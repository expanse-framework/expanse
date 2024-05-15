from collections.abc import Callable
from functools import wraps
from typing import Self

from expanse.container.container import Container
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.types.http.middleware import RequestHandler


class Pipeline:
    """
    A routing pipeline are composed of layers, like middleware, through which
    a request — and corresponding response — must go through.
    """

    def __init__(self, container: Container) -> None:
        self._container = container
        self._pipes: list[Callable[[Request, RequestHandler], Response]] = []
        self._request: Request | None = None

    def use(self, pipes: list[Callable[[Request, RequestHandler], Response]]) -> Self:
        self._pipes = pipes

        return self

    def send(self, request: Request) -> Self:
        self._request: Request = request

        return self

    def to(self, handler: RequestHandler) -> Response:
        try:
            return self._build_pipeline(handler)(self._request)
        except Exception as e:
            from expanse.contracts.debug.exception_handler import ExceptionHandler

            handler = self._container.make(ExceptionHandler)

            handler.report(e)

            return handler.render(self._request, e)

    def _build_pipeline(self, handler: RequestHandler) -> RequestHandler:
        stack = handler

        for pipe in self._pipes[::-1]:
            stack = self._wrap(pipe)(stack)

        return stack

    def _wrap(
        self, pipe: Callable[[Request, RequestHandler], Response]
    ) -> Callable[[RequestHandler], RequestHandler]:
        @wraps(pipe)
        def decorator(next_call: RequestHandler) -> Callable[[Request], Response]:
            @wraps(next_call)
            def handler(request: Request) -> Response:
                return pipe(request, next_call)

            return handler

        return decorator
