from collections.abc import Iterable
from typing import Any
from typing import NoReturn

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
from expanse.core.http.middleware.middleware import Middleware
from expanse.core.http.middleware.middleware_stack import MiddlewareStack
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.routing.route import Route
from expanse.routing.route_group import RouteGroup
from expanse.types import Environ
from expanse.types import StartResponse
from expanse.types import WSGIApp
from expanse.types.routing import Endpoint


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

    def _search(self, environ: Environ) -> WSGIApp:
        matcher = self._app.make(RouteMatcher)

        partial: Route | None = None

        routes = self._routes

        for group in self._groups:
            routes.extend(group.routes)

        for route in routes:
            # Determine if any route matches the incoming scope,
            # and hand over to the matching route if found.
            match = matcher.match(route, environ)
            if match == Match.FULL:
                return self._route_handler(route)
            elif match == Match.PARTIAL and partial is None:
                partial = route

        if partial is not None:
            # Partial matches.
            # These are cases where an endpoint is
            # able to handle the request, but is not a preferred option.
            # We use this in particular to deal with "405 Method Not Allowed".
            return self._route_handler(partial)

        # Default response
        return self._default_handler(self._default_endpoint)

    def _route_handler(self, route: Route) -> WSGIApp:
        def wrapper(environ: Environ, start_response: StartResponse) -> Iterable[bytes]:
            request = Request(environ, start_response)
            with self._app.create_scoped_container():
                response = self._handle_routed_request(route, request)

                return self._response_as_wsgi_app(response)(environ, start_response)

        return wrapper

    def _default_endpoint(self) -> NoReturn:
        raise HTTPException(status_code=404)

    def _default_handler(self, endpoint: Endpoint) -> WSGIApp:
        def wrapper(environ: Environ, start_response: StartResponse) -> Iterable[bytes]:
            request = Request(environ, start_response)

            response = self._handle_request(
                request, self._app._default_middlewares, endpoint
            )

            return self._response_as_wsgi_app(response)(environ, start_response)

        return wrapper

    def _handle_routed_request(self, route: Route, request: Request) -> Any:
        def endpoint_wrapper(container: Container) -> Response:
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

            return container.call(route.endpoint, **arguments)

        return self._handle_request(
            request,
            self._app._default_middlewares + route.get_middleware(),
            endpoint_wrapper,
        )

    def _handle_request(
        self,
        request: Request,
        middlewares: list[type[Middleware]],
        endpoint: Endpoint,
        *args: Any,
    ) -> Response:
        with self._app.create_scoped_container() as container:
            container.instance(Request, request)

            stack = MiddlewareStack(container, middlewares)

            return stack.handle(endpoint, *args)

    def _response_as_wsgi_app(self, response: Response) -> WSGIApp:
        return response.response

    def __call__(
        self, environ: Environ, start_response: StartResponse
    ) -> Iterable[bytes]:
        app = self._search(environ)

        return app(environ, start_response)
