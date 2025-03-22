from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Self

from expanse.container.container import Container
from expanse.contracts.routing.registrar import Registrar
from expanse.http.request import Request
from expanse.http.response import Response


if TYPE_CHECKING:
    from expanse.core.http.middleware.middleware import Middleware


class Router(Registrar, ABC):
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
