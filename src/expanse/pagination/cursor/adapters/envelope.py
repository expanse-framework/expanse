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
from expanse.pagination.cursor.cursor_paginator import CursorPaginator
from expanse.support._model_types import is_msgspec_struct
from expanse.support._model_types import is_pydantic_model


class CursorPaginationLinks(BaseModel):
    next: str | None = None
    prev: str | None = None


class CursorPaginationLinksStruct(msgspec.Struct):
    next: str | None = None
    prev: str | None = None


@dataclass
class Paginator[T]:
    items: Sequence[T]
    next_encoded_cursor: str | None
    previous_encoded_cursor: str | None

    @classmethod
    def create(cls, paginator: CursorPaginator[T], request: Request) -> "Paginator[T]":
        return Paginator(
            items=paginator.items,
            next_encoded_cursor=paginator.next_encoded_cursor,
            previous_encoded_cursor=paginator.previous_encoded_cursor,
        )


@dataclass
class Links:
    next: str | None = None
    prev: str | None = None


@dataclass
class PaginatorWithLinks[T](Paginator[T]):
    links: Links

    @classmethod
    def create(
        cls, paginator: CursorPaginator[T], request: Request
    ) -> "PaginatorWithLinks[T]":
        next_url: str | None = None
        prev_url: str | None = None

        query = QueryParameters(request.url.query)
        if paginator.next_encoded_cursor:
            query.set("cursor", paginator.next_encoded_cursor)
            next_url = request.url.replace(query=str(query)).full

        if paginator.previous_encoded_cursor:
            query.set("cursor", paginator.previous_encoded_cursor)
            prev_url = request.url.replace(query=str(query)).full

        links = Links(next=next_url, prev=prev_url)
        return PaginatorWithLinks(
            items=paginator.items,
            next_encoded_cursor=paginator.next_encoded_cursor,
            previous_encoded_cursor=paginator.previous_encoded_cursor,
            links=links,
        )


class Envelope:
    """
    A pagination variant that wraps paginated data in an envelope JSON object.
    """

    def __init__(self, with_links: bool = True) -> None:
        self._with_links: bool = with_links

    async def adapt(
        self, annotated: type[CursorPaginator], data: CursorPaginator, request: Request
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

        paginator_class = PaginatorWithLinks if self._with_links else Paginator
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
        __dict__["data"] = Field(validation_alias="items")
        __dict__["next_cursor"] = Field(validation_alias="next_encoded_cursor")
        __dict__["previous_cursor"] = Field(validation_alias="previous_encoded_cursor")

        __annotations__: dict[str, Any] = {}
        __annotations__["data"] = list[model]
        __annotations__["next_cursor"] = str | None
        __annotations__["previous_cursor"] = str | None

        if self._with_links:
            __annotations__["links"] = CursorPaginationLinks

        __dict__["__annotations__"] = __annotations__

        base_model = type("EnvelopeModel", (BaseModel,), __dict__)

        return base_model

    def _get_msgspec_model(self, model: Any) -> type[msgspec.Struct]:
        fields: list[tuple[str, Any] | tuple[str, Any, Any]] = [
            ("items", list[model]),
            ("next_encoded_cursor", str | None, None),
            ("previous_encoded_cursor", str | None, None),
        ]
        rename = {
            "items": "data",
            "next_encoded_cursor": "next_cursor",
            "previous_encoded_cursor": "previous_cursor",
        }

        if self._with_links:
            fields.append(("links", CursorPaginationLinksStruct))

        return msgspec.defstruct("EnvelopeModel", fields, rename=rename, kw_only=True)
