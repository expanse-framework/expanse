from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Protocol


if TYPE_CHECKING:
    from expanse.asynchronous.http.request import Request
    from expanse.asynchronous.http.response import Response
    from expanse.asynchronous.types.http.middleware import RequestHandler


class Middleware(Protocol):
    async def handle(self, request: Request, next_call: RequestHandler) -> Response: ...
