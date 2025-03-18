from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.core.http.exceptions import HTTPException
from expanse.http.response_adapter import ResponseAdapter
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.exceptions.handler import ExceptionHandler


class HTTPServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.exceptions.handler import ExceptionHandler

        self._container.scoped(ResponseAdapter)

        await self._container.on_resolved(
            ExceptionHandler, self._configure_exception_handler
        )

    async def _configure_exception_handler(self, handler: ExceptionHandler) -> None:
        from expanse.http.exceptions import CSRFTokenMismatchError

        handler.dont_report(CSRFTokenMismatchError)
        handler.prepare_using(
            CSRFTokenMismatchError, lambda e: HTTPException(419, str(e))
        )
