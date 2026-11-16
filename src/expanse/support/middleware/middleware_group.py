from typing import Self


class MiddlewareGroup[M]:
    def __init__(self, middlewares: list[type[M]] | None = None) -> None:
        self._middlewares = middlewares or []

    @property
    def middleware(self) -> list[type[M]]:
        return self._middlewares

    def append(self, *middleware: type[M]) -> Self:
        """
        Append middleware to the middleware stack.
        """
        self._middlewares.extend(middleware)

        return self

    def prepend(self, *middleware: type[M]) -> Self:
        """
        Prepend middleware to the middleware stack.
        """
        self._middlewares = [*middleware, *self._middlewares]

        return self

    def use(self, middleware: list[type[M]]) -> Self:
        """
        Replace the current middleware with the given middleware.
        """
        self._middlewares = middleware

        return self

    def replace(self, middleware: type[M], replacement: type[M]) -> Self:
        """
        Replace a middleware with another middleware.
        """
        index = self._middlewares.index(middleware)

        self._middlewares[index] = replacement

        return self

    def remove(self, middleware: type[M]) -> Self:
        """
        Remove a middleware from the middleware group.
        """
        self._middlewares.remove(middleware)

        return self
