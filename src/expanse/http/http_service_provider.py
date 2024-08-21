from __future__ import annotations

from expanse.http.response_adapter import ResponseAdapter
from expanse.support.service_provider import ServiceProvider


class HTTPServiceProvider(ServiceProvider):
    def register(self) -> None:
        self._container.singleton(ResponseAdapter)
