from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.routing.route import Route


if TYPE_CHECKING:
    from expanse.foundation.http.middleware.base import Middleware
    from expanse.types.routing import Endpoint


class RouteGroup:
    def __init__(
        self,
        name: str | None = None,
        prefix: str | None = None,
        middlewares: list[Middleware] | None = None,
    ) -> None:
        self.name: str | None = name
        self.prefix: str | None = prefix
        self.routes: list[Route] = []
        self.middlewares: list[type[Middleware]] = middlewares or []

    def get(self, path: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        route = Route.get(path, endpoint, name=name)

        self.add_route(route)

        return route

    def post(self, path: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        route = Route.post(path, endpoint, name=name)

        self.add_route(route)

        return route

    def add_route(self, route: Route) -> None:
        if route.name is not None and self.name is not None:
            route.name = f"{self.name}.{route.name}"

        self.routes.append(route)

    def add_routes(self, routes: list[Route]) -> None:
        for route in routes:
            self.add_route(route)
