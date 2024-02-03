from __future__ import annotations

import inspect
import re

from typing import TYPE_CHECKING
from typing import Awaitable
from typing import Callable

from starlette.middleware import Middleware as BaseMiddleware
from starlette.routing import Mount
from starlette.routing import Route as BaseRoute
from starlette.routing import Router as StarletteRouter

from expanse.foundation.http.middleware._adapter import AdapterMiddleware
from expanse.http.form import Form
from expanse.http.query import Query
from expanse.http.request import Request


if TYPE_CHECKING:
    from starlette.requests import Request as BaseRequest
    from starlette.responses import Response

    from expanse.foundation.application import Application
    from expanse.routing.route import Route
    from expanse.routing.route_group import RouteGroup
    from expanse.types import Receive
    from expanse.types import Scope
    from expanse.types import Send


class Router:
    def __init__(self, app: Application) -> None:
        self._app: Application = app
        self._router: StarletteRouter = StarletteRouter()

    def add_route(self, route: Route) -> None:
        self._router.add_route(
            route.path,
            self._route_handler(route),
            methods=route.methods,
            name=route.name,
        )

    def add_routes(self, routes: list[Route]) -> None:
        for route in routes:
            self.add_route(route)

    def add_group(self, group: RouteGroup) -> None:
        mount = Mount(
            group.prefix or "/",
            routes=[
                BaseRoute(
                    route.path,
                    self._route_handler(route),
                    methods=route.methods,
                    name=route.name,
                )
                for route in group.routes
            ],
            name=group.name,
            middleware=[
                BaseMiddleware(
                    AdapterMiddleware, middleware=middleware, container=self._app
                )
                for middleware in group.middlewares
                if hasattr(middleware, "handle")
            ],
        )

        self._router.routes.append(mount)

    def add_groups(self, groups: list[RouteGroup]) -> None:
        for group in groups:
            self.add_group(group)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self._router(scope, receive, send)

    def _route_handler(
        self, route: Route
    ) -> Callable[[BaseRequest], Awaitable[Response] | Response]:
        path_params = self._get_path_param_names(route)
        signature = self._get_typed_signature(route)

        async def wrapper(request: BaseRequest) -> Response:
            self._app.instance(Request, Request(request.scope), scoped=True)

            arguments = []

            for name, parameter in signature.parameters.items():
                if name in path_params:
                    arguments.append(request.path_params[name])
                elif isinstance(parameter.annotation, type) and issubclass(
                    parameter.annotation, Form
                ):
                    arguments.append(parameter.annotation(data=await request.form()))
                elif isinstance(parameter.annotation, type) and issubclass(
                    parameter.annotation, Query
                ):
                    arguments.append(parameter.annotation(params=request.query_params))

            return await self._app.call(route.endpoint, *arguments)

        return wrapper

    def _get_path_param_names(self, route: Route) -> set[str]:
        return set(re.findall(r"{([^:]*)(?::.*)?}", route.path))

    def _get_typed_signature(self, route: Route) -> inspect.Signature:
        return inspect.signature(route.endpoint)
