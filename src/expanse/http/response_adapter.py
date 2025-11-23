import contextlib

from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import asdict
from dataclasses import is_dataclass
from functools import partial
from typing import Annotated
from typing import Any
from typing import Self
from typing import TypeVar
from typing import get_args
from typing import get_origin

from expanse.container.container import Container
from expanse.http.response import Response
from expanse.support.has_adapter import HasAdapter


_Adapter = Callable[..., Awaitable[Response]] | Callable[..., Response]
_Serializer = Callable[..., Awaitable[dict[str, Any]]]
T = TypeVar("T")


class ResponseAdapter:
    def __init__(self, container: Container) -> None:
        self._container: Container = container
        self._adapters: dict[type, _Adapter] = {
            str: self._adapt_string,
            Sequence: self._adapt_sequence,
            dict: self._adapt_dict,
        }

    async def adapt(
        self, response: Any, declared_response_type: type | None = None
    ) -> Response:
        adapter = self.adapter(response, declared_response_type=declared_response_type)

        if adapter is None:
            adapter = self._adapt_via_adapter(response, declared_response_type)

            if not adapter:
                raise ValueError(
                    f"Cannot adapt type {type(response)} to a valid response"
                )

        return await self._container.call(
            adapter, response, expected_type=declared_response_type
        )

    def adapter(
        self, response: Any, declared_response_type: type | None = None
    ) -> _Adapter | None:
        for klass, adapter in self._adapters.items():
            if isinstance(response, klass):
                return adapter

        return self._adapter_with_serializer(response, declared_response_type)

    def register_adapter(self, response_type: type, adapter: _Adapter) -> Self:
        self._adapters[response_type] = adapter

        return self

    def _adapter_with_serializer(
        self, response: Any, declared_response_type: type | None = None
    ) -> _Adapter | None:
        serializer = self._find_serializer(response, declared_response_type)

        if not serializer:
            return None

        async def _adapter(response: Any, **kwargs) -> Response:
            from expanse.http.helpers import json

            return json(await serializer(response))

        return _adapter

    def _adapt_via_adapter(
        self, obj: Any, type_: type | None = None
    ) -> _Adapter | None:
        if not type_:
            type_ = obj.__class__

        origin = get_origin(type_)
        if origin is not Annotated:
            if isinstance(obj, HasAdapter):
                adapter = obj.get_adapter()

                return partial(adapter.adapt, type_)

            return None

        annotated, annotation = get_args(type_)

        if not hasattr(annotation, "adapt"):
            return None

        return partial(annotation.adapt, annotated)

    async def _adapt_string(
        self, response: str, container: Container, **kwargs
    ) -> Response:
        from expanse.http.helpers import json

        return json(response)

    async def _adapt_dict(
        self, response: dict[str, Any], container: Container
    ) -> Response:
        from expanse.http.helpers import json

        return json(response)

    async def _adapt_sequence(
        self,
        response: Sequence,
        container: Container,
        *,
        expected_type: type | None = None,
    ) -> Response:
        from expanse.http.helpers import json

        if expected_type is not None:
            origin: type | None = get_origin(expected_type)
            if (
                origin is not None
                and origin is not Annotated
                and issubclass(origin, Sequence)
            ):
                expected_type = get_args(expected_type)[0]

        serializer: _Serializer | None = None
        if len(response) > 0:
            serializer = self._find_serializer(response[0], expected_type)

        # Adapt each item in the sequence
        new_response: list[Any] = [
            await serializer(item) if serializer is not None else item
            for item in response
        ]

        return json(new_response)

    def _find_serializer(
        self, obj: Any, type_: type | None = None
    ) -> _Serializer | None:
        serializer: _Serializer | None = None
        if type_ is not None:
            origin = get_origin(type_)

            if origin is Annotated:
                from pydantic import BaseModel

                _, annotation = get_args(type_)
                is_pydantic_model = False

                with contextlib.suppress(TypeError):
                    is_pydantic_model = issubclass(annotation, BaseModel)

                if is_pydantic_model:

                    async def _serializer(model: Any) -> dict[str, Any]:
                        return annotation.model_validate(model).model_dump()

                    serializer = _serializer

        if serializer is None and is_dataclass(obj):

            async def _serializer(model: Any) -> dict[str, Any]:
                return asdict(model)

            serializer = _serializer

        return serializer
