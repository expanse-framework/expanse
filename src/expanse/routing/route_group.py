from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING
from typing import Self

from expanse.contracts.routing.registrar import Registrar
from expanse.routing.finder import Finder
from expanse.routing.route import Route


if TYPE_CHECKING:
    from collections.abc import Generator

    from expanse.contracts.routing.route_collection import (
        RouteCollection as RouteCollectionContract,
    )
    from expanse.core.http.middleware.middleware import Middleware
    from expanse.types.routing import Endpoint


class RouteGroup(Registrar):
    def __init__(
        self,
        name: str | None = None,
        prefix: str | None = None,
    ) -> None:
        self.name: str | None = name
        self.prefix: str | None = prefix
        self._routes = Finder()

        self._middlewares: list[type[Middleware] | str] = []

    @property
    def routes(self) -> RouteCollectionContract:
        return self._routes

    def add_route(self, route: Route) -> Route:
        route = self._build_route(route)
        self._routes.add(route)

        return route

    def add_routes(self, routes: list[Route]) -> None:
        for route in routes:
            self.add_route(route)

    def add_group(self, group: RouteGroup) -> None:
        for route in group.routes:
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

    def middleware(self, *middlewares: type[Middleware] | str) -> Self:
        self._middlewares.extend(middlewares)

        return self

    def prepend_middleware(self, *middlewares: type[Middleware] | str) -> Self:
        self._middlewares = list(middlewares) + self._middlewares

        return self

    @contextmanager
    def group(
        self,
        name: str | None = None,
        prefix: str | None = None,
    ) -> Generator[RouteGroup, None, None]:
        with super().group(name=name, prefix=prefix) as group:
            yield group

            self.add_group(group)

    def _build_route(self, route: Route) -> Route:
        route_name = route.name
        if route_name is not None and self.name is not None:
            route_name = f"{self.name}.{route.name}"

        if self.prefix:
            if not route.path:
                route_path = self.prefix
            else:
                route_path = "/".join([self.prefix, route.path]).replace("//", "/")
        else:
            route_path = route.path

        route = route.__class__(
            route.methods, route_path, route.endpoint, name=route_name
        )

        if self._middlewares:
            route.prepend_middleware(*self._middlewares)

        return route

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return
