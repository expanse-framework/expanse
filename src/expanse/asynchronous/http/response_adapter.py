from typing import Any
from typing import Protocol
from typing import Self
from typing import TypeVar

from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response


T = TypeVar("T")


class _Adapter(Protocol):
    async def __call__(self, raw_response: T, *args: Any) -> Response: ...


class _SyncAdapter(Protocol):
    def __call__(self, raw_response: T, *args: Any) -> Response: ...


class ResponseAdapter:
    def __init__(self) -> None:
        self._adapters: dict[
            type[T],
            _Adapter | _SyncAdapter,
        ] = {str: self._adapt_string}

    def adapter(self, response: Any) -> _Adapter | _SyncAdapter:
        for klass, adapter in self._adapters.items():
            if isinstance(response, klass):
                return adapter

        raise ValueError(f"Cannot adapt type {type(response)} to a valid response")

    def register_adapter(
        self,
        response_type: type[T],
        adapter: _Adapter | _SyncAdapter,
    ) -> Self:
        self._adapters[response_type] = adapter

        return self

    def _adapt_string(self, request: Request, response: str) -> Response:
        if request.expects_json():
            return Response.json(response)

        return Response.text(response)
