from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING
from typing import Self

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.routing.route_collection import RouteCollection
from expanse.contracts.routing.router import Router as RouterContract
from expanse.core.http.exceptions import HTTPException
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.http.response_adapter import ResponseAdapter
from expanse.routing.finder import Finder
from expanse.routing.pipeline import Pipeline
from expanse.routing.route import Route
from expanse.routing.route_group import RouteGroup
from expanse.support._concurrency import should_run_as_async
from expanse.support._concurrency import sync_to_async
from expanse.support._concurrency import warn_about_implicit_async_safe_status
from expanse.types.http.middleware import RequestHandler
from expanse.types.routing import Endpoint


if TYPE_CHECKING:
    from expanse.core.http.middleware.middleware import Middleware


class Router(RouterContract):
    def __init__(self, config: Config) -> None:
        self._config: Config = config
        self._finder: Finder = Finder()
        self._middleware_groups: dict[str, list[type[Middleware]]] = {}

    @property
    def routes(self) -> RouteCollection:
        return self._finder

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

    def add_route(self, route: Route) -> Route:
        self._finder.add(route)

        return route

    def add_routes(self, routes: list[Route]) -> None:
        for route in routes:
            self.add_route(route)

    def add_group(self, group: RouteGroup) -> None:
        for route in group.routes:
            self.add_route(route)

    def add_groups(self, groups: list[RouteGroup]) -> None:
        for group in groups:
            self.add_group(group)

    @contextmanager
    def group(
        self,
        name: str | None = None,
        prefix: str | None = None,
    ) -> Generator[RouteGroup, None, None]:
        with super().group(name=name, prefix=prefix) as group:
            yield group

            self.add_group(group)

    def middleware_group(self, name: str, middleware: list[type["Middleware"]]) -> Self:
        self._middleware_groups[name] = middleware

        return self

    async def handle(self, container: Container, request: Request) -> Response:
        route = self._finder.match(request)

        if route is None:
            raise HTTPException(404, "Not found.")

        handler: RequestHandler

        # Set the route to the request
        request.set_route(route)

        handler = self._route_handler(route, container)

        pipes: list[Callable[[Request, RequestHandler], Awaitable[Response]]] = []
        for middleware in route.get_middleware():
            if isinstance(middleware, str):
                if middleware not in self._middleware_groups:
                    raise ValueError(
                        f"Middleware group '{middleware}' not found in the middleware groups."
                    )

                for group_middleware in self._middleware_groups[middleware]:
                    pipes.append((await container.get(group_middleware)).handle)

                continue

            pipes.append((await container.get(middleware)).handle)

        return await Pipeline(container).use(pipes).send(request).to(handler)

    def _route_handler(self, route: Route, container: Container) -> RequestHandler:
        async def handler(request: Request) -> Response:
            compiled = route.compile()
            arguments, _ = await compiled.bind(request)

            if isinstance(compiled.handler, tuple):
                instance: type = await container.get(compiled.handler[0])
                handler = getattr(instance, compiled.handler[1])
            else:
                handler = compiled.handler

            positional, keywords = await container._resolve_signature(
                compiled.signature, kwargs=arguments, callable=handler
            )

            if compiled.is_async:
                raw_response = await handler(*positional, **keywords)
            elif not should_run_as_async(handler):
                warn_about_implicit_async_safe_status(handler, self._config)

                raw_response = handler(*positional, **keywords)
            else:
                raw_response = await sync_to_async(handler, *positional, **keywords)

            # Do not go through the response adapter if the response is already a Response instance
            if isinstance(raw_response, Response):
                return raw_response

            declared_response_type = compiled.signature.return_annotation

            adapter = await container.get(ResponseAdapter)

            return await adapter.adapt(
                raw_response, declared_response_type=declared_response_type
            )

        return handler
