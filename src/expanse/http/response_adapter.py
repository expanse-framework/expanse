from collections.abc import Callable
from typing import Any
from typing import Self
from typing import TypeVar
from typing import Unpack


try:
    from typing import TypeVarTuple
except ImportError:
    from typing_extensions import TypeVarTuple

from expanse.http.request import Request
from expanse.http.response import Response


T = TypeVar("T")
Ts = TypeVarTuple("Ts")


class ResponseAdapter:
    def __init__(self) -> None:
        self._adapters: dict[type[T], Callable[[[Unpack[Ts], T], T], Response]] = {
            str: self._adapt_string
        }

    def adapter(self, response: Any) -> Callable[[[Unpack[Ts], T], T], Response]:
        for klass, adapter in self._adapters.items():
            if isinstance(response, klass):
                return adapter

        raise ValueError(f"Cannot adapt type {type(response)} to a valid response")

    def register_adapter(
        self, response_type: type[T], adapter: Callable[[Unpack[Ts], T], Response]
    ) -> Self:
        self._adapters[response_type] = adapter

        return self

    def _adapt_string(self, request: Request, response: str) -> Response:
        if request.expects_json():
            return Response.json(response)

        return Response.text(response)
