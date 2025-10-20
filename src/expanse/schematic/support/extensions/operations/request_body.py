from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.schematic.analyzers.schema_generator import SchemaGenerator
from expanse.schematic.openapi.media_type import MediaType
from expanse.schematic.openapi.request_body import RequestBody
from expanse.schematic.support.extensions.operations.extension import OperationExtension
from expanse.schematic.support.route_info import RouteInfo


if TYPE_CHECKING:
    from expanse.schematic.openapi.operation import Operation


class RequestBodyExtension(OperationExtension):
    def handle(self, operation: Operation, route_info: RouteInfo) -> None:
        description = route_info.doc_string.description

        operation.set_summary(route_info.doc_string.summary or "").set_description(
            description or ""
        )
        signature_info = route_info.signature
        # Check if there's a body parameter
        body_param = signature_info.body_parameter
        form_param = signature_info.form_parameter

        if body_param and body_param.pydantic_model:
            # Create request body with Pydantic model
            request_body = RequestBody()
            request_body.set_required(body_param.is_required)

            # Add description from docstring
            if body_param.name in route_info.doc_string.parameters:
                param_doc = route_info.doc_string.parameters[body_param.name]
                if param_doc.description:
                    request_body.set_description(param_doc.description)

            # TODO: Use schema reference in media type
            # component_name = schema_generator.get_or_create_component_schema(
            #    body_param.pydantic_model, components.schemas
            # )
            # schema_ref = Reference(f"#/components/schemas/{component_name}")

            media_type = MediaType()
            schema = SchemaGenerator().generate_from_pydantic(body_param.pydantic_model)
            media_type.set_schema(schema)

            request_body.add_content("application/json", media_type)

            operation.set_request_body(request_body)

        elif form_param:
            request_body = RequestBody()
            request_body.set_required(form_param.is_required)

            if form_param.name in route_info.doc_string.parameters:
                param_doc = route_info.doc_string.parameters[form_param.name]
                if param_doc.description:
                    request_body.set_description(param_doc.description)

            # Create media type for form data
            schema = SchemaGenerator().generate_from_type(form_param.annotation)
            media_type = MediaType(schema)

            request_body.add_content("multipart/form-data", media_type)

            operation.set_request_body(request_body)
