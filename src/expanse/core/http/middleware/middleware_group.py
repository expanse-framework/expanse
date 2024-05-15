from typing import Self

from expanse.core.http.middleware.middleware import Middleware


class MiddlewareGroup:
    def __init__(self, middlewares: list[type[Middleware]] | None = None) -> None:
        self._middlewares = middlewares or []

    def append(self, *middleware: type[Middleware]) -> Self:
        """
        Append middleware to the middleware stack.
        """
        self._middlewares.extend(middleware)

        return self

    def prepend(self, *middleware: type[Middleware]) -> Self:
        """
        Prepend middleware to the middleware stack.
        """
        self._middlewares = [*middleware, *self._middlewares]

        return self

    def use(self, middleware: list[type[Middleware]]) -> Self:
        """
        Replace the current middleware with the given middleware.
        """
        self._middlewares = middleware

        return self
