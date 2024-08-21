from collections import defaultdict
from collections.abc import Iterator
from typing import ClassVar
from typing import NoReturn

from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.route import Route
from expanse.common.core.http.exceptions import HTTPException
from expanse.common.routing.route import Match
from expanse.common.routing.route_matcher import RouteMatcher


class RouteCollection:
    METHODS: ClassVar[list[str]] = [
        "GET",
        "HEAD",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ]

    def __init__(self) -> None:
        self._routes: list[Route] = []
        self._routes_by_method: dict[str, list[Route]] = defaultdict(list)
        self._route_matcher: RouteMatcher = RouteMatcher()

    def add(self, route: Route) -> None:
        self._routes.append(route)

        for method in route.methods:
            self._routes_by_method[method.upper()].append(route)

    def match(self, request: Request):
        routes = self.get(request.method)

        route = self.get_matching_route(request, routes)

        return self._handle_route(request, route)

    def get(self, method: str | None = None) -> list[Route]:
        if method is None:
            return self._routes

        return self._routes_by_method.get(method.upper(), [])

    def get_matching_route(
        self, request: Request, routes: list[Route], allow_partial: bool = False
    ) -> Route | None:
        for route in routes:
            match = self._route_matcher.match(route, request)
            if match == Match.FULL:
                return route

            if match == Match.PARTIAL and allow_partial:
                return route

        return None

    def _handle_route(self, request: Request, route: Route | None) -> Route | None:
        if route is not None:
            return route

        # No route was found.
        # We will check if there is a route that matches the request but with
        # a different method.
        methods = self._check_for_alternative_methods(request)
        if methods:
            return self._get_route_for_methods(request, methods)

        raise HTTPException(404, f"Route {request.url.path} could not be found")

    def _check_for_alternative_methods(self, request: Request) -> list[str]:
        methods = []
        for method, routes in self._routes_by_method.items():
            if method == request.method:
                continue

            routes = self.get(method)

            if self.get_matching_route(request, routes, allow_partial=True) is not None:
                methods.append(method)
                continue

        return methods

    def _get_route_for_methods(
        self, request: Request, methods: list[str]
    ) -> Route | None:
        if request.method == "OPTIONS":

            async def endpoint() -> Response:
                return Response(
                    "", status_code=200, headers={"Allow": ", ".join(methods)}
                )

            return Route(request.url.path, endpoint, methods=["OPTIONS"])

        self._method_not_allowed(request, methods)

    def _method_not_allowed(self, request: Request, methods: list[str]) -> NoReturn:
        raise HTTPException(
            405,
            f"The method {request.method} is not supported for route {request.url.path}. "
            f"Available methods: {', '.join(methods)}",
            headers={"Allow": ", ".join(methods)},
        )

    def __iter__(self) -> Iterator[Route]:
        return iter(self._routes)
