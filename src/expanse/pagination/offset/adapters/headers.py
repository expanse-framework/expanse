from dataclasses import dataclass
from typing import Annotated
from typing import Any
from typing import Self
from typing import get_args
from typing import get_origin

from expanse.http.helpers import json
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.http.url import QueryParameters
from expanse.pagination.offset.paginator import Paginator


@dataclass(frozen=True)
class Link:
    name: str
    url: str

    @classmethod
    def for_page(cls, name: str, page: int, request: Request) -> Self:
        query = QueryParameters(request.url.query)
        query.set("page", str(page))
        url = request.url.replace(query=str(query)).full

        return cls(name=name, url=url)

    def as_header(self) -> str:
        return f'<{self.url}>; rel="{self.name}"'


class Headers:
    async def adapt(
        self, annotated: type[Paginator], data: Paginator, request: Request
    ) -> Response:
        paginator_args = get_args(annotated)

        if not paginator_args:
            raise TypeError("CursorPaginator must have a type argument")

        items: list[Any] = list(data.items)
        item_type = paginator_args[0]
        origin = get_origin(item_type)

        if origin is Annotated:
            _, page_model = get_args(item_type)
            items = [
                page_model.model_validate(item, from_attributes=True).model_dump()
                for item in data.items
            ]

        links = []

        if data.next_page is not None:
            next_link = Link.for_page("next", data.next_page, request)
            links.append(next_link.as_header())

        if data.previous_page is not None:
            prev_link = Link.for_page("prev", data.previous_page, request)
            links.append(prev_link.as_header())

        first_link = Link.for_page("first", data.first_page, request)
        links.append(first_link.as_header())

        last_link = Link.for_page("last", data.last_page, request)
        links.append(last_link.as_header())

        self_link = Link.for_page("self", data.current_page, request)
        links.append(self_link.as_header())

        response = json(
            content=items,
            headers={"X-Total-Count": str(data.total), "Link": ", ".join(links)},
        )

        return response
