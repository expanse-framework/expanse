import sys

from abc import ABC
from abc import abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

from expanse.contracts.routing.route_collection import RouteCollection
from expanse.routing.route import Route
from expanse.support._utils import module_from_path
from expanse.types.routing import Endpoint


if TYPE_CHECKING:
    from expanse.routing.route_group import RouteGroup


class Registrar(ABC):
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

    @contextmanager
    def group(
        self,
        name: str | None = None,
        prefix: str | None = None,
    ) -> Generator["RouteGroup", None, None]:
        from expanse.routing.route_group import RouteGroup

        group = RouteGroup(name=name, prefix=prefix)

        yield group

    def load_file(self, path: Path, base_path: Path | None = None) -> None:
        """
        Load routes from a file.

        The file should contain a function named `routes` that accepts a `Registrar` instance.

        :param path: The path to the file.
        """
        module = self._load_module(path, base_path=base_path)

        if module is None:
            return

        routes = module.routes

        routes(self)

    def _load_module(
        self, path: Path, base_path: Path | None = None
    ) -> ModuleType | None:
        path = relative_path = path.resolve()

        if base_path is not None:
            relative_path = path.relative_to(base_path)

        module_name = relative_path.with_suffix("").as_posix().replace("/", ".")

        module = module_from_path(path, name=module_name)

        if module is None:
            return None

        # Register route file to sys.modules
        if module_name not in sys.modules:
            sys.modules[module_name] = module

        return module
