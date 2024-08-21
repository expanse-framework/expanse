from __future__ import annotations

from expanse.asynchronous.http.response_adapter import ResponseAdapter
from expanse.asynchronous.support.service_provider import ServiceProvider


class HTTPServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(ResponseAdapter)
