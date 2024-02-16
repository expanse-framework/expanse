from typing import Self

from expanse.common.routing.route_group import RouteGroup as BaseRouteGroup
from expanse.foundation.http.middleware.middleware import Middleware
from expanse.routing.route import Route


class RouteGroup(BaseRouteGroup):
    def __init__(
        self,
        name: str | None = None,
        prefix: str | None = None,
    ) -> None:
        super().__init__(name, prefix)

        self._middlewares: list[type[Middleware]] = []

    def middleware(self, *middlewares: type[Middleware]) -> Self:
        self._middlewares.extend(middlewares)

        return self

    def prepend_middleware(self, *middlewares: type[Middleware]) -> Self:
        self._middlewares = list(middlewares) + self._middlewares

        return self

    def _build_route(self, route: Route) -> Route:
        route = super()._build_route(route)

        if self._middlewares:
            route.prepend_middleware(*self._middlewares)

        return route
