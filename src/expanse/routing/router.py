from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING
from typing import Annotated
from typing import NoReturn
from typing import get_args
from typing import get_origin

from pydantic import BaseModel

from expanse.container.container import Container
from expanse.http.form import Form
from expanse.http.helpers import abort
from expanse.http.json import JSON
from expanse.http.query import Query
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.http.response_adapter import ResponseAdapter
from expanse.routing.pipeline import Pipeline
from expanse.routing.route import Route
from expanse.routing.route_collection import RouteCollection
from expanse.routing.route_group import RouteGroup
from expanse.types.http.middleware import RequestHandler
from expanse.types.routing import Endpoint


if TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable


class Router:
    def __init__(self, container: Container) -> None:
        self._container: Container = container
        self._routes: RouteCollection = RouteCollection()

    @property
    def routes(self) -> RouteCollection:
        return self._routes

    def add_route(self, route: Route) -> None:
        self._routes.add(route)

    def add_routes(self, routes: list[Route]) -> None:
        for route in routes:
            self.add_route(route)

    def add_group(self, group: RouteGroup) -> None:
        for route in group.routes:
            self.add_route(route)

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

    @contextmanager
    def group(
        self,
        name: str | None = None,
        prefix: str | None = None,
    ) -> Generator[RouteGroup]:
        group = RouteGroup(name=name, prefix=prefix)

        yield group

        self.add_group(group)

    def find(self, name: str) -> Route | None:
        return self._routes.find(name)

    async def handle(self, container: Container, request: Request) -> Response:
        route = self._routes.match(request)

        handler: RequestHandler
        pipes: list[Callable[[Request, RequestHandler], Awaitable[Response]]] = []
        if route is None:
            # No matching route was found, so we use the default handler
            # to handle the request.
            handler = self._default_handler(container)
        else:
            # Set the route to the request
            request.set_route(route)

            handler = self._route_handler(route, container)
            pipes = [
                (await container.get(middleware)).handle
                for middleware in route.get_middleware()
            ]

        return await Pipeline(container).use(pipes).send(request).to(handler)

    def _route_handler(self, route: Route, container: Container) -> RequestHandler:
        async def handler(request: Request) -> Response:
            arguments = {}

            for name, parameter in route.signature.parameters.items():
                if name in route.param_names:
                    arguments[name] = request.path_params[name]
                elif isinstance(parameter.annotation, type) and issubclass(
                    parameter.annotation, Form
                ):
                    arguments[name] = parameter.annotation(await request.form)
                elif get_origin(parameter.annotation) is Annotated and issubclass(
                    (origin_args := get_args(parameter.annotation))[0], BaseModel
                ):
                    validation_model: type[BaseModel] = origin_args[0]

                    data_type: type[JSON] | type[Query] | JSON | Query = origin_args[1]

                    if isinstance(data_type, JSON) or issubclass(data_type, JSON):  # type: ignore[arg-type, misc]
                        arguments[name] = validation_model.model_validate(
                            await request.json
                        )
                    elif isinstance(data_type, Query) or issubclass(data_type, Query):  # type: ignore[arg-type, misc]
                        arguments[name] = validation_model.model_validate(
                            request.query_params
                        )

            raw_response = await container.call(route.endpoint, **arguments)

            # Do not go through the response adapter if the response is already a Response instance
            if isinstance(raw_response, Response):
                return raw_response

            declared_response_type = route.signature.return_annotation

            adapter = await container.get(ResponseAdapter)
            return await adapter.adapt(
                raw_response, declared_response_type=declared_response_type
            )

        return handler

    def _default_handler(self, container: Container) -> RequestHandler:
        async def handler(request: Request) -> NoReturn:
            abort(404)

        return handler
