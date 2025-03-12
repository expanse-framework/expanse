from abc import ABC
from abc import abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING
from typing import Self

from expanse.container.container import Container
from expanse.contracts.routing.route_collection import RouteCollection
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.routing.route import Route
from expanse.routing.route_group import RouteGroup
from expanse.types.routing import Endpoint


if TYPE_CHECKING:
    from expanse.core.http.middleware.middleware import Middleware


class Router(ABC):
    @property
    @abstractmethod
    def routes(self) -> RouteCollection: ...

    @abstractmethod
    def get(self, uri: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        """
        Register a new GET route.

        :param uri: The URI of the route.
        :param endpoint: The route handler.
        :param name: The name of the route.
        """
        ...

    @abstractmethod
    def post(self, uri: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        """
        Register a new POST route.

        :param uri: The URI of the route.
        :param endpoint: The route handler.
        :param name: The name of the route.
        """
        ...

    @abstractmethod
    def put(self, uri: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        """
        Register a new PUT route.

        :param uri: The URI of the route.
        :param endpoint: The route handler.
        :param name: The name of the route.
        """
        ...

    @abstractmethod
    def patch(self, uri: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        """
        Register a new PATCH route.

        :param uri: The URI of the route.
        :param endpoint: The route handler.
        :param name: The name of the route.
        """
        ...

    @abstractmethod
    def delete(self, uri: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        """
        Register a new DELETE route.

        :param uri: The URI of the route.
        :param endpoint: The route handler.
        :param name: The name of the route.
        """
        ...

    @abstractmethod
    def head(self, uri: str, endpoint: Endpoint, *, name: str | None = None) -> Route:
        """
        Register a new HEAD route.

        :param uri: The URI of the route.
        :param endpoint: The route handler.
        :param name: The name of the route.
        """
        ...

    @abstractmethod
    def options(
        self, uri: str, endpoint: Endpoint, *, name: str | None = None
    ) -> Route:
        """
        Register a new OPTIONS route.

        :param uri: The URI of the route.
        :param endpoint: The route handler.
        :param name: The name of the route.
        """
        ...

    @abstractmethod
    async def handle(self, container: Container, request: Request) -> Response:
        """
        Handle an incoming request.

        :param container: The scoped service container.
        :param request: The incoming request.
        """
        ...

    @abstractmethod
    def middleware_group(
        self, name: str, middleware: list[type["Middleware"]]
    ) -> Self: ...

    @contextmanager
    def group(
        self,
        name: str | None = None,
        prefix: str | None = None,
    ) -> Generator[RouteGroup, None, None]:
        group = RouteGroup(name=name, prefix=prefix)

        yield group
