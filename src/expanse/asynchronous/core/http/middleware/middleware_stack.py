from typing import Self

from expanse.asynchronous.core.http.middleware.middleware import Middleware
from expanse.asynchronous.core.http.middleware.middleware_group import MiddlewareGroup


class MiddlewareStack:
    def __init__(self, middlewares: list[type[Middleware]] | None = None) -> None:
        self._middlewares: list[type[Middleware]] = middlewares or []
        self._groups: dict[str, MiddlewareGroup] = {}

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

    def group(self, name: str) -> MiddlewareGroup:
        """
        Retrieve the middleware group with the given name.

        If does not exist it will be created automatically.
        """
        if name not in self._groups:
            self._groups[name] = MiddlewareGroup()

        return self._groups[name]