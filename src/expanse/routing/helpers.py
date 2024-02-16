from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.routing.route import Route
from expanse.routing.route_group import RouteGroup


if TYPE_CHECKING:
    from expanse.types.routing import Endpoint


def get(path: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
    return Route.get(path, endpoint, name=name)


def post(path: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
    return Route.post(path, endpoint, name=name)


def put(path: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
    return Route.put(path, endpoint, name=name)


def patch(path: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
    return Route.patch(path, endpoint, name=name)


def delete(path: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
    return Route.delete(path, endpoint, name=name)


def group(name: str | None = None, prefix: str | None = None) -> RouteGroup:
    return RouteGroup(name=name, prefix=prefix)
