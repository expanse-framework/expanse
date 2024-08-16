from collections.abc import Callable
from typing import Any
from typing import Self

from expanse.container.container import Container
from expanse.http.request import Request
from expanse.http.response import Response


_Adapter = Callable[..., Response]


class ResponseAdapter:
    def __init__(self) -> None:
        self._adapters: dict[type, _Adapter] = {str: self._adapt_string}

    def adapter(self, response: Any) -> _Adapter:
        for klass, adapter in self._adapters.items():
            if isinstance(response, klass):
                return adapter

        raise ValueError(f"Cannot adapt type {type(response)} to a valid response")

    def register_adapter(self, response_type: type, adapter: _Adapter) -> Self:
        self._adapters[response_type] = adapter

        return self

    def _adapt_string(
        self, response: str, request: Request, container: Container
    ) -> Response:
        from expanse.routing.responder import Responder

        responder = container.make(Responder)

        if request.expects_json():
            return responder.json(response)

        return responder.text(response)
