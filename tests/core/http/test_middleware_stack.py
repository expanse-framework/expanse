from expanse.core.http.middleware.middleware_stack import MiddlewareStack
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.types.http.middleware import RequestHandler


class Middleware1:
    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        return await next_call(request)


class Middleware2:
    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        return await next_call(request)


class Middleware3:
    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        return await next_call(request)


def test_remove_middleware() -> None:
    stack = MiddlewareStack()
    stack.use([Middleware1, Middleware2])

    assert len(stack.middleware) == 2

    stack.remove(Middleware1)

    assert len(stack.middleware) == 1


def test_replace_middleware() -> None:
    stack = MiddlewareStack()
    stack.use([Middleware1, Middleware2])

    assert len(stack.middleware) == 2

    stack.replace(Middleware1, Middleware3)

    assert len(stack.middleware) == 2
    assert Middleware1 not in stack.middleware
