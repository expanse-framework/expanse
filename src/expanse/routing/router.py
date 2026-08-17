from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Generator
from contextlib import contextmanager
from functools import partial
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any
from typing import Self
from typing import get_args
from typing import get_origin

import msgspec

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.routing.route_collection import RouteCollection
from expanse.contracts.routing.router import Router as RouterContract
from expanse.core.http.exceptions import HTTPException
from expanse.http.form import Form
from expanse.http.json import JSON
from expanse.http.query import Query
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
from expanse.support._model_types import is_msgspec_struct
from expanse.support._model_types import is_pydantic_model
from expanse.types.http.middleware import RequestHandler
from expanse.types.routing import Endpoint


if TYPE_CHECKING:
    from expanse.core.http.middleware.middleware import Middleware


class _ArgumentBinder:
    """
    How to pull one endpoint parameter's value out of a request, decided
    once per route (see `_compile_argument_binders()`) instead of being
    re-derived from the signature's type annotations on every request.
    """

    __slots__ = ("is_async", "name", "resolve")

    def __init__(
        self, name: str, is_async: bool, resolve: Callable[[Request], Any]
    ) -> None:
        self.name = name
        self.is_async = is_async
        self.resolve = resolve


def _bind_path_param(request: Request, *, name: str) -> Any:
    return request.path_params[name]


async def _bind_form(request: Request, *, annotation: type[Form]) -> Form:
    return annotation(await request.form)


async def _bind_json(request: Request, *, model: Any, is_pydantic: bool) -> Any:
    raw = await request.json

    if is_pydantic:
        return model.model_validate(raw)

    return msgspec.convert(raw, type=model, strict=False)


def _bind_query(request: Request, *, model: Any, is_pydantic: bool) -> Any:
    if is_pydantic:
        return model.model_validate(request.query_params)

    return msgspec.convert(request.query_params, type=model, strict=False)


def _compile_argument_binders(route: Route) -> list[_ArgumentBinder]:
    """
    Precomputes, once per route, how each parameter that needs a value
    pulled from the request (path params, form/JSON/query-validated models)
    should be bound. Parameters not covered here are left for DI to
    resolve.
    """
    binders: list[_ArgumentBinder] = []

    for name, parameter in route.signature.parameters.items():
        if name in route.param_names:
            binders.append(
                _ArgumentBinder(name, False, partial(_bind_path_param, name=name))
            )
            continue

        annotation = parameter.annotation

        if isinstance(annotation, type) and issubclass(annotation, Form):
            binders.append(
                _ArgumentBinder(name, True, partial(_bind_form, annotation=annotation))
            )
            continue

        if get_origin(annotation) is not Annotated:
            continue

        validation_model, data_type = get_args(annotation)

        if not (
            is_pydantic_model(validation_model) or is_msgspec_struct(validation_model)
        ):
            continue

        is_pydantic = is_pydantic_model(validation_model)

        if isinstance(data_type, JSON) or issubclass(data_type, JSON):  # type: ignore[arg-type]
            binders.append(
                _ArgumentBinder(
                    name,
                    True,
                    partial(
                        _bind_json, model=validation_model, is_pydantic=is_pydantic
                    ),
                )
            )
        elif isinstance(data_type, Query) or issubclass(data_type, Query):  # type: ignore[arg-type]
            binders.append(
                _ArgumentBinder(
                    name,
                    False,
                    partial(
                        _bind_query, model=validation_model, is_pydantic=is_pydantic
                    ),
                )
            )

    return binders


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
        route.argument_binders = _compile_argument_binders(route)

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
        binders: list[_ArgumentBinder] = route.argument_binders

        async def handler(request: Request) -> Response:
            arguments: dict[str, Any] = {}

            for binder in binders:
                if binder.is_async:
                    arguments[binder.name] = await binder.resolve(request)
                else:
                    arguments[binder.name] = binder.resolve(request)

            if isinstance(route.endpoint, tuple):
                instance: type = await container.get(route.endpoint[0])
                endpoint = getattr(instance, route.endpoint[1])
            else:
                endpoint = route.endpoint

            positional, keywords = await container._resolve_signature(
                route.signature, kwargs=arguments, callable=endpoint
            )

            if route.is_async:
                raw_response = await endpoint(*positional, **keywords)
            elif not should_run_as_async(endpoint):
                warn_about_implicit_async_safe_status(endpoint, self._config)

                raw_response = endpoint(*positional, **keywords)
            else:
                raw_response = await sync_to_async(endpoint, *positional, **keywords)

            # Do not go through the response adapter if the response is already a Response instance
            if isinstance(raw_response, Response):
                return raw_response

            declared_response_type = route.signature.return_annotation

            adapter = await container.get(ResponseAdapter)

            return await adapter.adapt(
                raw_response, declared_response_type=declared_response_type
            )

        return handler
