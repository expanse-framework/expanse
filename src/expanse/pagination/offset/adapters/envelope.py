from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated
from typing import Any
from typing import get_args
from typing import get_origin

import msgspec

from pydantic import BaseModel
from pydantic import Field

from expanse.http.helpers import json
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.http.url import QueryParameters
from expanse.pagination.offset.paginator import Paginator
from expanse.support._model_types import is_msgspec_struct
from expanse.support._model_types import is_pydantic_model


class OffsetPaginationLinks(BaseModel):
    next: str | None
    prev: str | None
    first: str
    last: str
    self: str


class OffsetPaginationLinksStruct(msgspec.Struct):
    next: str | None
    prev: str | None
    first: str
    last: str
    self: str


@dataclass
class PaginatorModel:
    items: Sequence[Any]
    next_page: int | None
    previous_page: int | None
    current_page: int
    first_page: int
    last_page: int
    total: int

    @classmethod
    def create(cls, paginator: Paginator[Any], request: Request) -> "PaginatorModel":
        return PaginatorModel(
            items=paginator.items,
            next_page=paginator.next_page,
            previous_page=paginator.previous_page,
            current_page=paginator.current_page,
            first_page=paginator.first_page,
            last_page=paginator.last_page,
            total=paginator.total,
        )


@dataclass
class Links:
    next: str | None
    prev: str | None
    first: str
    last: str
    self: str


@dataclass
class PaginatorWithLinks(PaginatorModel):
    links: Links

    @classmethod
    def create(
        cls, paginator: Paginator[Any], request: Request
    ) -> "PaginatorWithLinks":
        next_url: str | None = None
        prev_url: str | None = None

        query = QueryParameters(request.url.query)
        if paginator.next_page is not None:
            query.set("page", str(paginator.next_page))
            next_url = request.url.replace(query=str(query)).full

        if paginator.previous_page is not None:
            query.set("page", str(paginator.previous_page))
            prev_url = request.url.replace(query=str(query)).full

        query.set("page", str(paginator.first_page))
        first_url = request.url.replace(query=str(query)).full

        query.set("page", str(paginator.last_page))
        last_url = request.url.replace(query=str(query)).full

        query.set("page", str(paginator.current_page))
        self_url = request.url.replace(query=str(query)).full

        links = Links(
            next=next_url, prev=prev_url, first=first_url, last=last_url, self=self_url
        )
        return PaginatorWithLinks(
            items=paginator.items,
            next_page=paginator.next_page,
            previous_page=paginator.previous_page,
            current_page=paginator.current_page,
            first_page=paginator.first_page,
            last_page=paginator.last_page,
            total=paginator.total,
            links=links,
        )


class Envelope:
    """
    A pagination variant that wraps paginated data in an envelope JSON object.
    """

    def __init__(self, with_links: bool = True) -> None:
        self._with_links: bool = with_links

    async def adapt(
        self, annotated: type[Paginator], data: Paginator, request: Request
    ) -> Response:
        paginator_args = get_args(annotated)

        if not paginator_args:
            raise TypeError("CursorPaginator must have a type argument")

        item_type = paginator_args[0]
        origin = get_origin(item_type)

        if origin is Annotated:
            _, page_model = get_args(item_type)
            model = self.get_model(page_model)
        else:
            model = self.get_model(item_type)

        paginator_class = PaginatorWithLinks if self._with_links else PaginatorModel
        paginator = paginator_class.create(data, request)

        if is_msgspec_struct(model):
            content = msgspec.to_builtins(
                msgspec.convert(
                    paginator, type=model, from_attributes=True, strict=False
                )
            )

            return json(content)

        assert is_pydantic_model(model)

        return json(model.model_validate(paginator, from_attributes=True).model_dump())

    def get_model(self, model: Any) -> type[BaseModel] | type[msgspec.Struct]:
        """
        Create a model for the envelope structure, matching the kind of the
        item DTO (Pydantic model or msgspec struct), so the whole envelope is
        serialized through a single, consistent library.

        The model is dynamic based on the envelope configuration.
        """
        if is_msgspec_struct(model):
            return self._get_msgspec_model(model)

        return self._get_pydantic_model(model)

    def _get_pydantic_model(self, model: Any) -> type[BaseModel]:
        from pydantic import BaseModel

        __dict__: dict[str, Any] = {}
        __dict__["data"] = Field(alias="items")
        __dict__["next_page"] = Field(None, ge=1)
        __dict__["previous_page"] = Field(..., ge=1)
        __dict__["current_page"] = Field(..., ge=1)
        __dict__["first_page"] = Field(..., ge=1)
        __dict__["last_page"] = Field(..., ge=1)

        model_name: str = (
            "OffsetEnvelopeWithoutLinks" if not self._with_links else "OffsetEnvelope"
        )
        __annotations__: dict[str, Any] = {}
        __annotations__["data"] = list[model]
        __annotations__["next_page"] = int | None
        __annotations__["previous_page"] = int | None
        __annotations__["current_page"] = int
        __annotations__["first_page"] = int
        __annotations__["last_page"] = int
        __annotations__["total"] = int

        if self._with_links:
            __annotations__["links"] = OffsetPaginationLinks

        __dict__["__annotations__"] = __annotations__

        base_model = type(model_name, (BaseModel,), __dict__)

        return base_model

    def _get_msgspec_model(self, model: Any) -> type[msgspec.Struct]:
        positive_int = Annotated[int, msgspec.Meta(ge=1)]

        fields: list[tuple[str, Any] | tuple[str, Any, Any]] = [
            ("items", list[model]),
            ("previous_page", positive_int | None),
            ("current_page", positive_int),
            ("first_page", positive_int),
            ("last_page", positive_int),
            ("total", int),
            ("next_page", positive_int | None, None),
        ]
        rename = {"items": "data"}

        model_name: str = (
            "OffsetEnvelopeWithoutLinks" if not self._with_links else "OffsetEnvelope"
        )

        if self._with_links:
            fields.append(("links", OffsetPaginationLinksStruct))

        return msgspec.defstruct(model_name, fields, rename=rename, kw_only=True)


__all__ = ["Envelope"]
