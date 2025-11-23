from __future__ import annotations

import textwrap

from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any
from typing import get_args
from typing import get_origin

from expanse.pagination.cursor.cursor_paginator import CursorPaginator
from expanse.pagination.offset.paginator import Paginator
from expanse.schematic.openapi.header import Header
from expanse.schematic.openapi.media_type import MediaType
from expanse.schematic.openapi.response import Response as OpenAPIResponse
from expanse.schematic.openapi.schema import Schema
from expanse.schematic.openapi.types import ArrayType
from expanse.schematic.openapi.types import StringType
from expanse.schematic.support.extensions.operations.extension import OperationExtension


if TYPE_CHECKING:
    from expanse.schematic.openapi.operation import Operation
    from expanse.schematic.support.route_info import RouteInfo
    from expanse.support.adapter import Adapter


class PaginationResponseExtension(OperationExtension):
    """
    Extension to detect and add responses.

    It does not handle error responses.
    """

    def handle(self, operation: Operation, route_info: RouteInfo) -> None:
        signature = route_info.signature
        annotation = signature.return_annotation
        origin = get_origin(annotation)

        # Checking if the route returns any paginator
        if origin is CursorPaginator or origin is Paginator:
            return self.handle_paginator(
                annotation, annotation.get_adapter(), operation, route_info
            )
        elif origin is Annotated:
            annotated, adapter = get_args(annotation)
            return self.handle_paginator(annotated, adapter, operation, route_info)

    def handle_paginator(
        self,
        annotation: type[Paginator] | type[CursorPaginator],
        adapter: Adapter,
        operation: Operation,
        route_info: RouteInfo,
    ) -> None:
        origin = get_origin(annotation)
        args = get_args(annotation)

        schema: Schema | None = None
        headers: dict[str, Header] = {}
        if not args:
            # We don't have a type for paginated items so we use a generic pagination object instead
            if origin is CursorPaginator:
                schema, headers = self.get_cursor_paginator_schema(adapter, Any)

            elif origin is Paginator:
                schema, headers = self.get_offset_paginator_schema(adapter, Any)

        elif get_origin(args[0]) is Annotated:
            # The paginated item is annotated with a model
            item_model = get_args(args[0])[1]

            if origin is CursorPaginator:
                schema, headers = self.get_cursor_paginator_schema(adapter, item_model)
            elif origin is Paginator:
                schema, headers = self.get_offset_paginator_schema(adapter, item_model)
        else:
            # The paginated item is not annotated with a model
            # so we use a generic pagination object instead
            if origin is CursorPaginator:
                schema, headers = self.get_cursor_paginator_schema(adapter, Any)

            elif origin is Paginator:
                schema, headers = self.get_offset_paginator_schema(adapter, Any)

        if schema is None:
            return

        response = operation.responses.get_response("200")
        if response is None:
            response = OpenAPIResponse(description="Successful Response")
            operation.responses.add_response("200", response)

        assert isinstance(response, OpenAPIResponse)

        media_type = MediaType(schema)
        response.add_content("application/json", media_type)
        response.headers.update(headers)

    def get_cursor_paginator_schema(
        self,
        adapter: Adapter,
        item_model: type[Any],
    ) -> tuple[Schema | None, dict[str, Header]]:
        from expanse.pagination.cursor.adapters.envelope import Envelope
        from expanse.pagination.cursor.adapters.headers import Headers

        schema: Schema | None = None
        headers: dict[str, Header] = {}

        if isinstance(adapter, Envelope):
            model = adapter.get_model(item_model)
            schema = self._schema_registry.generate_from_pydantic(
                model, type="response"
            )
        elif isinstance(adapter, Headers):
            ref, _ = self._schema_registry.get_or_create_component_schema(
                item_model, type="response"
            )
            items = ArrayType()
            items.items = ref
            schema = Schema(items)
            header = Header()
            header.schema = Schema(StringType())
            header.description = textwrap.dedent(
                """\
                Links to specific pages, in the format defined by
                [RFC 5988](https://tools.ietf.org/html/rfc5988#section-5).
                This will include a link with relation type `next` to the
                next page, if there is a next page.\
                """
            )
            headers["Link"] = header

        return schema, headers

    def get_offset_paginator_schema(
        self,
        adapter: Adapter,
        item_model: type[Any],
    ) -> tuple[Schema | None, dict[str, Header]]:
        from expanse.pagination.offset.adapters.envelope import Envelope
        from expanse.pagination.offset.adapters.headers import Headers

        headers: dict[str, Header] = {}
        schema: Schema | None = None

        if isinstance(adapter, Envelope):
            model = adapter.get_model(item_model)
            schema = self._schema_registry.generate_from_pydantic(
                model, type="response"
            )
        elif isinstance(adapter, Headers):
            ref, _ = self._schema_registry.get_or_create_component_schema(
                item_model, type="response"
            )
            items = ArrayType()
            items.items = ref
            schema = Schema(items)
            header = Header()
            header.schema = Schema(StringType())
            header.description = textwrap.dedent(
                """\
                Links to specific pages, in the format defined by
                [RFC 5988](https://tools.ietf.org/html/rfc5988#section-5).
                This will include a link with relation type `next` to the
                next page, if there is a next page.\
                """
            )
            headers["Link"] = header

        return schema, headers
