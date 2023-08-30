from __future__ import annotations

from typing import TYPE_CHECKING
from typing import AsyncGenerator
from typing import Protocol


if TYPE_CHECKING:
    from expanse.http.request import Request
    from expanse.http.response import Response


class Middleware(Protocol):
    async def handle(
        self, request: Request
    ) -> AsyncGenerator[Response | None, Response]:
        ...
