from collections.abc import Callable

from expanse.http.request import Request
from expanse.http.response import Response


RequestHandler = Callable[[Request], Response]
