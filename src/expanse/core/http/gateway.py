from collections.abc import Iterable
from functools import partial
from typing import Self

from expanse.core.application import Application
from expanse.core.http.middleware.middleware import Middleware
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.routing.pipeline import Pipeline
from expanse.routing.router import Router
from expanse.types import Environ
from expanse.types import StartResponse


class Gateway:
    """
    The gateway is the layer between the WSGI spec/world and Expanse internal
    architecture.
    """

    def __init__(self, app: Application, router: Router) -> None:
        self._app = app
        self._router = router
        self._middleware: list[type[Middleware]] = []
        self._group_middleware: dict[str, list[type[Middleware]]] = {}

    def handle(self, request: Request) -> Response:
        with self._app.container.create_scoped_container() as container:
            container.instance(Request, request)

            return (
                Pipeline(container)
                .use(
                    [
                        container.make(middleware).handle
                        for middleware in self._middleware
                    ]
                )
                .send(request)
                .to(partial(self._router.handle, container))
            )

    def set_middleware(self, middleware: list[type[Middleware]]) -> Self:
        self._middleware = middleware

        return self

    def prepend_middleware(self, middleware: type[Middleware]) -> Self:
        if middleware not in self._middleware:
            self._middleware.insert(0, middleware)

        return self

    def append_middleware(self, middleware: type[Middleware]) -> Self:
        if middleware not in self._middleware:
            self._middleware.append(middleware)

        return self

    def __call__(
        self, environ: Environ, start_response: StartResponse
    ) -> Iterable[bytes]:
        request = Request(environ, start_response)

        response = self.handle(request)

        return self._prepare_response(response, environ, start_response)

    def _prepare_response(
        self, response: Response, environ: Environ, start_response: StartResponse
    ) -> Iterable[bytes]:
        return response(environ, start_response)
