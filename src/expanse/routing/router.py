from typing import TYPE_CHECKING
from typing import Any

from expanse.common.core.http.exceptions import HTTPException
from expanse.common.http.form import Form
from expanse.common.http.json import JSON
from expanse.common.http.query import Query
from expanse.common.http.url_path import URLPath
from expanse.common.routing.exceptions import RouteNotFound
from expanse.common.routing.route import Match
from expanse.common.routing.route_matcher import RouteMatcher
from expanse.container.container import Container
from expanse.core.application import Application
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.http.response_adapter import ResponseAdapter
from expanse.routing.pipeline import Pipeline
from expanse.routing.route import Route
from expanse.routing.route_group import RouteGroup
from expanse.types.http.middleware import RequestHandler
from expanse.types.routing import Endpoint


if TYPE_CHECKING:
    from collections.abc import Callable


class Router:
    def __init__(self, app: Application) -> None:
        self._app: Application = app
        self._routes: list[Route] = []
        self._groups: list[RouteGroup] = []

    def add_route(self, route: Route) -> None:
        self._routes.append(route)

    def add_routes(self, routes: list[Route]) -> None:
        for route in routes:
            self.add_route(route)

    def add_group(self, group: RouteGroup) -> None:
        self._groups.append(group)

    def add_groups(self, groups: list[RouteGroup]) -> None:
        for group in groups:
            self.add_group(group)

    def get(self, path: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        route = Route.get(path, endpoint, name=name)
        self.add_route(route)

        return route

    def post(self, path: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        route = Route.post(path, endpoint, name=name)
        self.add_route(route)

        return route

    def put(self, path: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        route = Route.put(path, endpoint, name=name)
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

    def group(
        self,
        name: str | None = None,
        prefix: str | None = None,
    ) -> RouteGroup:
        group = RouteGroup(name=name, prefix=prefix)
        self.add_group(group)

        return group

    def route(self, name: str, parameters: dict[str, Any] | None = None) -> URLPath:
        parameters = parameters or {}

        for route in self._routes:
            if route.name == name:
                matcher = self._app.make(RouteMatcher)

                return matcher.url(route.path, **parameters)

        for group in self._groups:
            for route in group.routes:
                if route.name == name:
                    matcher = self._app.make(RouteMatcher)

                    return matcher.url(route.path, **parameters)

        raise RouteNotFound(f"Route [{name}] is not defined")

    def url(self, path: str, parameters: dict[str, Any] | None = None) -> URLPath:
        matcher = self._app.make(RouteMatcher)

        parameters = parameters or {}

        return matcher.url(path, **parameters)

    def handle(self, container: Container, request: Request) -> Response:
        route = self._search(request)

        handler: RequestHandler
        pipes: list[Callable[[Request, RequestHandler], Response]] = []
        if route is None:
            # No matching route was found, so we use the default handler
            # to handle the request.
            handler = self._default_handler(container)
        else:
            handler = self._route_handler(route, container)
            pipes = [
                container.make(middleware).handle
                for middleware in route.get_middleware()
            ]

        return Pipeline(container).use(pipes).send(request).to(handler)

    def _search(self, request: Request) -> Route | None:
        matcher = self._app.make(RouteMatcher)

        partial: Route | None = None

        routes = self._routes

        for group in self._groups:
            routes.extend(group.routes)

        for route in routes:
            # Determine if any route matches the incoming request,
            # and hand over to the matching route if found.
            match = matcher.match(route, request)
            if match == Match.FULL:
                return route
            elif match == Match.PARTIAL and partial is None:
                partial = route

        if partial is not None:
            # Partial matches.
            # These are cases where an endpoint is
            # able to handle the request, but is not a preferred option.
            # We use this in particular to deal with "405 Method Not Allowed".
            return partial

        return None

    def _route_handler(self, route: Route, container: Container) -> RequestHandler:
        def handler(request: Request) -> Response:
            if route.methods and request.method not in route.methods:
                headers = {"Allow": ", ".join(route.methods)}

                raise HTTPException(status_code=405, headers=headers)

            arguments = {}

            for name, parameter in route.signature.parameters.items():
                if name in route.param_names:
                    arguments[name] = request.path_params[name]
                elif isinstance(parameter.annotation, type) and issubclass(
                    parameter.annotation, JSON
                ):
                    arguments[name] = parameter.annotation(data=request.json)
                elif isinstance(parameter.annotation, type) and issubclass(
                    parameter.annotation, Form
                ):
                    arguments[name] = parameter.annotation(request.form)

                elif isinstance(parameter.annotation, type) and issubclass(
                    parameter.annotation, Query
                ):
                    arguments[name] = parameter.annotation(params=request.query_params)

            raw_response = container.call(route.endpoint, **arguments)

            # Do not go through the response adapter if the response is already a Response instance
            if isinstance(raw_response, Response):
                return raw_response

            return container.call(
                container.make(ResponseAdapter).adapter(raw_response), raw_response
            )

        return handler

    def _default_handler(self, _: Container) -> RequestHandler:
        def handler(request: Request) -> Response:
            raise Response.abort(404)

        return handler
