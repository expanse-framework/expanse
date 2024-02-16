from collections.abc import Awaitable
from collections.abc import Callable

from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response


RequestHandler = Callable[[Request], Awaitable[Response]]
