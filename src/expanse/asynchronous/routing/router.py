from typing import Any
from typing import NoReturn

from baize.asgi.responses import Response as BaizeResponse

from expanse.asynchronous.container.container import Container
from expanse.asynchronous.foundation.application import Application
from expanse.asynchronous.foundation.http.middleware.middleware import Middleware
from expanse.asynchronous.foundation.http.middleware.middleware_stack import (
    MiddlewareStack,
)
from expanse.asynchronous.http.form import Form
from expanse.asynchronous.http.query import Query
from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.types import ASGIApp
from expanse.asynchronous.types import Receive
from expanse.asynchronous.types import Scope
from expanse.asynchronous.types import Send
from expanse.asynchronous.types.routing import Endpoint
from expanse.common.foundation.http.exceptions import HTTPException
from expanse.common.http.url_path import URLPath
from expanse.common.routing.exceptions import RouteNotFound
from expanse.common.routing.route import Match
from expanse.common.routing.route import Route
from expanse.common.routing.route_group import RouteGroup
from expanse.common.routing.route_matcher import RouteMatcher


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

    async def url(self, path: str, /, **parameters: Any) -> URLPath:
        matcher = await self._app.make(RouteMatcher)

        return matcher.url(path, **parameters)

    async def route(self, name: str, /, **parameters: Any) -> URLPath:
        for route in self._routes:
            if route.name == name:
                matcher = await self._app.make(RouteMatcher)

                return matcher.url(route.path, **parameters)

        raise RouteNotFound(f"Route [{name}] is not defined")

    async def _search(self, scope: Scope) -> ASGIApp:
        matcher = await self._app.make(RouteMatcher)

        partial: Route | None = None

        routes = self._routes

        for group in self._groups:
            routes.extend(group.routes)

        for route in routes:
            # Determine if any route matches the incoming scope,
            # and hand over to the matching route if found.
            match = matcher.match(route, scope=scope)
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

    def _route_handler(self, route: Route) -> ASGIApp:
        async def wrapper(scope: Scope, receive: Receive, send: Send) -> None:
            request = Request(scope, receive, send)
            async with self._app.create_scoped_container():
                response = await self._handle_routed_request(route, request)
                app = await self._adapt_response(response)

                return await app(scope, receive, send)

        return wrapper

    def _default_endpoint(self) -> NoReturn:
        raise HTTPException(status_code=404)

    def _default_handler(self, endpoint: Endpoint) -> ASGIApp:
        async def wrapper(scope: Scope, receive: Receive, send: Send) -> None:
            request = Request(scope, receive, send)

            response = await self._handle_request(
                request, self._app._default_middlewares, endpoint
            )
            app = await self._adapt_response(response)

            return await app(scope, receive, send)

        return wrapper

    async def _handle_routed_request(self, route: Route, request: Request) -> Response:
        async def endpoint_wrapper(container: Container) -> Response:
            if route.methods and request.method not in route.methods:
                headers = {"Allow": ", ".join(route.methods)}

                raise HTTPException(status_code=405, headers=headers)

            arguments = {}

            for name, parameter in route.signature.parameters.items():
                if name in route.param_names:
                    arguments[name] = request.path_params[name]
                elif isinstance(parameter.annotation, type) and issubclass(
                    parameter.annotation, Form
                ):
                    arguments[name] = parameter.annotation(data=await request.form)
                elif isinstance(parameter.annotation, type) and issubclass(
                    parameter.annotation, Query
                ):
                    arguments[name] = parameter.annotation(params=request.query_params)

            return await container.call(route.endpoint, **arguments)

        return await self._handle_request(
            request,
            self._app._default_middlewares + route.get_middleware(),
            endpoint_wrapper,
        )

    async def _handle_request(
        self,
        request: Request,
        middlewares: list[type[Middleware]],
        endpoint: Endpoint,
        *args: Any,
    ) -> Response:
        async with self._app.create_scoped_container() as container:
            container.instance(Request, request)

            stack = MiddlewareStack(container, middlewares)

            return await stack.handle(endpoint, *args)

    async def _adapt_response(self, response: Any) -> ASGIApp:
        if isinstance(response, BaizeResponse):
            return response

        if isinstance(response, Response):
            return response.response

        raise ValueError(f"Cannot adapt type {type(response)} to a valid response")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        app = await self._search(scope)

        return await app(scope, receive, send)