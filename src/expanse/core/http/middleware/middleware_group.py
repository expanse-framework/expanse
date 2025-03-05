from typing import Self

from expanse.core.http.middleware.middleware import Middleware


class MiddlewareGroup:
    def __init__(self, middlewares: list[type[Middleware]] | None = None) -> None:
        self._middlewares = middlewares or []

    @property
    def middleware(self) -> list[type[Middleware]]:
        return self._middlewares

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

    def replace(
        self, middleware: type[Middleware], replacement: type[Middleware]
    ) -> Self:
        """
        Replace a middleware with another middleware.
        """
        index = self._middlewares.index(middleware)

        self._middlewares[index] = replacement

        return self

    def remove(self, middleware: type[Middleware]) -> Self:
        """
        Remove a middleware from the middleware group.
        """
        self._middlewares.remove(middleware)

        return self
