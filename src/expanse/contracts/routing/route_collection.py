from abc import ABC
from abc import abstractmethod
from collections.abc import Iterator

from expanse.http.request import Request
from expanse.routing.route import Route


class RouteCollection(ABC):
    @abstractmethod
    def add(self, route: Route) -> None:
        """
        Add a route to the collection.

        :param route: The route to add to the collection.
        """

    @abstractmethod
    def match(self, request: Request) -> Route | None:
        """
        Find the route that matches the given request.

        :param request: The Request to match.
        """
        ...

    @abstractmethod
    def find(self, name: str) -> Route | None:
        """
        Find a route by its name.

        :param name: The name of the route to find.
        """
        ...

    @abstractmethod
    def __iter__(self) -> Iterator[Route]:
        """
        Iterate over the routes in the collection.
        """
        ...
