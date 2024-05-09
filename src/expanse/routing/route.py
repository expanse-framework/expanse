from typing import Self

from expanse.common.routing.route import Route as BaseRoute
from expanse.core.http.middleware.middleware import Middleware
from expanse.types.routing import Endpoint


class Route(BaseRoute):
    def __init__(
        self,
        path: str,
        endpoint: Endpoint,
        *,
        methods: list[str] | None = None,
        name: str | None = None,
    ) -> None:
        super().__init__(path, endpoint, methods=methods, name=name)

        self._middlewares: list[type[Middleware]] = []

    def get_middleware(self) -> list[type[Middleware]]:
        return self._middlewares

    def middleware(self, *middlewares: type[Middleware]) -> Self:
        self._middlewares.extend(middlewares)

        return self

    def prepend_middleware(self, *middlewares: type[Middleware]) -> Self:
        self._middlewares = list(middlewares) + self._middlewares

        return self
