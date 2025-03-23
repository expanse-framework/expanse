import inspect

from collections.abc import Callable
from dataclasses import dataclass

from expanse.core.http.middleware.middleware import Middleware
from expanse.types.routing import Endpoint


@dataclass
class HandlerDefinition:
    method: str
    uri: str
    name: str | None
    middleware: type[Middleware] | str | None


def get(
    uri: str, name: str | None = None, middleware: type[Middleware] | str | None = None
) -> Callable[[Endpoint], Endpoint]:
    return _create_decorator("GET", uri, name, middleware)


def post(
    uri: str, name: str | None = None, middleware: type[Middleware] | str | None = None
) -> Callable[[Endpoint], Endpoint]:
    return _create_decorator("POST", uri, name, middleware)


def put(
    uri: str, name: str | None = None, middleware: type[Middleware] | str | None = None
) -> Callable[[Endpoint], Endpoint]:
    return _create_decorator("PUT", uri, name, middleware)


def patch(
    uri: str, name: str | None = None, middleware: type[Middleware] | str | None = None
) -> Callable[[Endpoint], Endpoint]:
    return _create_decorator("PATCH", uri, name, middleware)


def delete(
    uri: str, name: str | None = None, middleware: type[Middleware] | str | None = None
) -> Callable[[Endpoint], Endpoint]:
    return _create_decorator("DELETE", uri, name, middleware)


def group(
    name: str | None = None,
    prefix: str | None = None,
) -> Callable[[type], type]:
    def decorator(controller: type) -> type:
        setattr(controller, "__route_group__", (name, prefix))  # noqa: B010

        return controller

    return decorator


def _create_decorator(
    method: str,
    uri: str,
    name: str | None,
    middleware: type[Middleware] | str | None,
) -> Callable[[Endpoint], Endpoint]:
    def decorator(handler: Endpoint) -> Endpoint:
        definition = HandlerDefinition(method, uri, name, middleware)
        setattr(handler, "__route_definition__", definition)  # noqa: B010

        module = inspect.getmodule(handler)
        if module is None:
            return handler

        if not hasattr(module, "__route_handlers__"):
            setattr(module, "__route_handlers__", [])  # noqa: B010

        module.__route_handlers__.append(handler)

        return handler

    return decorator
