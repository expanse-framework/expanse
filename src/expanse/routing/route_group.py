from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Self

from expanse.common.routing.route_group import RouteGroup as BaseRouteGroup
from expanse.routing.route import Route


if TYPE_CHECKING:
    from expanse.core.http.middleware.middleware import Middleware
    from expanse.routing.router import Router
    from expanse.types.routing import Endpoint


class RouteGroup(BaseRouteGroup):
    def __init__(
        self,
        name: str | None = None,
        prefix: str | None = None,
    ) -> None:
        super().__init__(name, prefix)

        self._middlewares: list[type[Middleware]] = []

    def add_routes(self, routes: list[Route] | Router) -> None:
        from expanse.routing.router import Router

        if isinstance(routes, Router):
            for route in routes._routes:
                self.add_route(route)

            for group in routes._groups:
                for route in group.routes:
                    self.add_route(route)

            return

        for route in routes:
            self.add_route(route)

    def get(self, path: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        route = Route.get(path, endpoint, name=name)
        self.add_route(route)

        return route

    def post(self, path: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        route = Route.post(path, endpoint, name=name)
        self.add_route(route)

        return route

    def put(self, path: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        route = Route.patch(path, endpoint, name=name)
        self.add_route(route)

        return route

    def patch(self, path: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        route = Route.patch(path, endpoint, name=name)
        self.add_route(route)

        return route

    def delete(
        self, path: str, endpoint: Endpoint, *, name: str | None = None
    ) -> Route:
        route = Route.delete(path, endpoint, name=name)
        self.add_route(route)

        return route

    def head(self, path: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        route = Route.head(path, endpoint, name=name)
        self.add_route(route)

        return route

    def options(
        self, path: str, endpoint: Endpoint, *, name: str | None = None
    ) -> Route:
        route = Route.options(path, endpoint, name=name)
        self.add_route(route)

        return route

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

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return
