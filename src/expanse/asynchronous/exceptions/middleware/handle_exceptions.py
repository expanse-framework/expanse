from expanse.asynchronous.container.container import Container
from expanse.asynchronous.contracts.debug.exception_handler import ExceptionHandler
from expanse.asynchronous.foundation.http.middleware.middleware import Middleware
from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.types.http.middleware import RequestHandler


class HandleExceptions(Middleware):
    def __init__(self, container: Container) -> None:
        self._container = container

    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        try:
            return await next_call(request)
        except Exception as e:
            handler = await self._container.make(ExceptionHandler)

            await handler.report(e)

            return await handler.render(request, e)
