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
        self._request = request

        return self

    def to(self, handler: RequestHandler) -> Response:
        from expanse.core.helpers import _set_container

        if not self._request:
            raise ValueError("No request has been set")

        assert self._request is not None

        _set_container(self._container)

        try:
            return self._build_pipeline(handler)(self._request)
        except Exception as e:
            from expanse.contracts.debug.exception_handler import ExceptionHandler

            if not self._container.has(ExceptionHandler):
                raise e

            exception_handler = self._container.make(ExceptionHandler)

            exception_handler.report(e)

            return exception_handler.render(self._request, e)
        finally:
            _set_container(None)

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
