from collections.abc import Awaitable
from collections.abc import Callable
from functools import wraps
from typing import Self

from expanse.asynchronous.container.container import Container
from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.types.http.middleware import RequestHandler


class Pipeline:
    """
    A routing pipeline are composed of layers, like middleware, through which
    a request — and corresponding response — must go through.
    """

    def __init__(self, container: Container) -> None:
        self._container = container
        self._pipes: list[Callable[[Request, RequestHandler], Awaitable[Response]]] = []
        self._request: Request | None = None

    def use(
        self, pipes: list[Callable[[Request, RequestHandler], Awaitable[Response]]]
    ) -> Self:
        self._pipes = pipes

        return self

    def send(self, request: Request) -> Self:
        self._request = request

        return self

    async def to(self, handler: RequestHandler) -> Response:
        if self._request is None:
            raise RuntimeError("No request has been set on the pipeline.")

        from expanse.asynchronous.core.helpers import _set_container

        _set_container(self._container)

        try:
            pipeline = await self._build_pipeline(handler)
            return await pipeline(self._request)
        except Exception as e:
            from expanse.asynchronous.contracts.debug.exception_handler import (
                ExceptionHandler,
            )

            if not self._container.has(ExceptionHandler):
                raise e

            exception_handler = await self._container.make(ExceptionHandler)

            await exception_handler.report(e)

            return await exception_handler.render(self._request, e)
        finally:
            _set_container(None)

    async def _build_pipeline(self, handler: RequestHandler) -> RequestHandler:
        stack = handler

        for pipe in self._pipes[::-1]:
            stack = await self._wrap(pipe)(stack)

        return stack

    def _wrap(
        self, pipe: Callable[[Request, RequestHandler], Awaitable[Response]]
    ) -> Callable[[RequestHandler], Awaitable[RequestHandler]]:
        @wraps(pipe)
        async def decorator(
            next_call: RequestHandler,
        ) -> Callable[[Request], Awaitable[Response]]:
            @wraps(next_call)
            async def handler(request: Request) -> Response:
                return await pipe(request, next_call)

            return handler

        return decorator
