from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.http.form import Form
from expanse.schematic.openapi.media_type import MediaType
from expanse.schematic.openapi.request_body import RequestBody
from expanse.schematic.support.extensions.operations.extension import OperationExtension


if TYPE_CHECKING:
    from expanse.schematic.openapi.operation import Operation
    from expanse.schematic.support.route_info import RouteInfo


class RequestBodyExtension(OperationExtension):
    def handle(self, operation: Operation, route_info: RouteInfo) -> None:
        description = route_info.doc_string.description

        operation.set_summary(route_info.doc_string.summary or "").set_description(
            description or ""
        )
        signature_info = route_info.signature
        body_param = signature_info.body_parameter

        if body_param and body_param.pydantic_model:
            # Create request body with Pydantic model
            request_body = RequestBody()
            request_body.set_required(body_param.is_required)

            # Add description from docstring
            if body_param.name in route_info.doc_string.parameters:
                param_doc = route_info.doc_string.parameters[body_param.name]
                if param_doc.description:
                    request_body.set_description(param_doc.description)

            reference, _ = self._schema_registry.get_or_create_component_schema(
                body_param.pydantic_model
            )
            media_type = MediaType(reference)
            content_type = "application/json"
            if body_param.data_source == Form:
                content_type = "multipart/form-data"

            request_body.add_content(content_type, media_type)

            operation.set_request_body(request_body)

        elif body_param:
            request_body = RequestBody()
            request_body.set_required(body_param.is_required)

            schema = self._schema_registry.generate_from_type(body_param.annotation)

            media_type = MediaType(schema)
            content_type = "application/json"

            request_body.add_content(content_type, media_type)
            operation.set_request_body(request_body)
