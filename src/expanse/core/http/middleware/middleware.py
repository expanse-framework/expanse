from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Protocol


if TYPE_CHECKING:
    from expanse.http.request import Request
    from expanse.http.response import Response
    from expanse.types.http.middleware import RequestHandler


class Middleware(Protocol):
    def handle(self, request: Request, next_call: RequestHandler) -> Response: ...
