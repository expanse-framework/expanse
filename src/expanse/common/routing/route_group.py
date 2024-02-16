from __future__ import annotations

from typing import Generic
from typing import TypeVar

from expanse.common.routing.route import Route


RouteT = TypeVar("RouteT", bound=Route)


class RouteGroup(Generic[RouteT]):
    def __init__(
        self,
        name: str | None = None,
        prefix: str | None = None,
    ) -> None:
        self.name: str | None = name
        self.prefix: str | None = prefix
        self.routes: list[RouteT] = []

    def add_route(self, route: RouteT) -> None:
        self.routes.append(self._build_route(route))

    def add_routes(self, routes: list[RouteT]) -> None:
        for route in routes:
            self.add_route(route)

    def _build_route(self, route: RouteT) -> RouteT:
        route_name = route.name
        if route_name is not None and self.name is not None:
            route_name = f"{self.name}.{route.name}"

        if self.prefix:
            route_path = "/".join([self.prefix, route.path]).replace("//", "/")
        else:
            route_path = route.path

        return route.__class__(
            route_path, route.endpoint, methods=route.methods, name=route_name
        )
