from typing import Self

from expanse.support.middleware.middleware_group import MiddlewareGroup


class MiddlewareStack[M]:
    def __init__(self, middlewares: list[type[M]] | None = None) -> None:
        if middlewares is None:
            middlewares = self.get_default_middleware()

        self._middlewares: list[type[M]] = middlewares
        self._groups: dict[str, MiddlewareGroup[M]] = self.get_default_groups()

    @property
    def middleware(self) -> list[type[M]]:
        return self._middlewares

    @property
    def groups(self) -> dict[str, MiddlewareGroup[M]]:
        return self._groups

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
        Remove a middleware from the stack.
        """
        self._middlewares.remove(middleware)

        return self

    def group(self, name: str) -> MiddlewareGroup[M]:
        """
        Retrieve the middleware group with the given name.

        If does not exist it will be created automatically.
        """
        if name not in self._groups:
            self._groups[name] = MiddlewareGroup()

        return self._groups[name]

    def get_default_middleware(self) -> list[type[M]]:
        return []

    def get_default_groups(self) -> dict[str, MiddlewareGroup[M]]:
        return {}
