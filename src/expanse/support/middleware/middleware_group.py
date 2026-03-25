from typing import Self

from expanse.support.middleware.middleware import Middleware


class MiddlewareGroup[I, O]:
    def __init__(self, middlewares: list[type[Middleware[I, O]]] | None = None) -> None:
        self._middlewares = middlewares or []

    @property
    def middleware(self) -> list[type[Middleware[I, O]]]:
        return self._middlewares

    def append(self, *middleware: type[Middleware[I, O]]) -> Self:
        """
        Append middleware to the middleware stack.
        """
        self._middlewares.extend(middleware)

        return self

    def prepend(self, *middleware: type[Middleware[I, O]]) -> Self:
        """
        Prepend middleware to the middleware stack.
        """
        self._middlewares = [*middleware, *self._middlewares]

        return self

    def use(self, middleware: list[type[Middleware[I, O]]]) -> Self:
        """
        Replace the current middleware with the given middleware.
        """
        self._middlewares = middleware

        return self

    def replace(
        self, middleware: type[Middleware[I, O]], replacement: type[Middleware[I, O]]
    ) -> Self:
        """
        Replace a middleware with another middleware.
        """
        index = self._middlewares.index(middleware)

        self._middlewares[index] = replacement

        return self

    def remove(self, middleware: type[Middleware[I, O]]) -> Self:
        """
        Remove a middleware from the middleware group.
        """
        self._middlewares.remove(middleware)

        return self
