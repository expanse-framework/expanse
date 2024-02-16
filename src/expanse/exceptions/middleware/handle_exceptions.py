from expanse.container.container import Container
from expanse.contracts.debug.exception_handler import ExceptionHandler
from expanse.foundation.http.middleware.middleware import Middleware
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.types.http.middleware import RequestHandler


class HandleExceptions(Middleware):
    def __init__(self, container: Container) -> None:
        self._container = container

    def handle(self, request: Request, next_call: RequestHandler) -> Response:
        try:
            return next_call(request)
        except Exception as e:
            handler = self._container.make(ExceptionHandler)

            handler.report(e)

            return handler.render(request, e)
