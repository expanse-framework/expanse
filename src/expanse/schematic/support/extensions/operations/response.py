from __future__ import annotations

from types import NoneType
from typing import TYPE_CHECKING

from pydantic import BaseModel
from pydantic import Field

from expanse.schematic.openapi.media_type import MediaType
from expanse.schematic.openapi.response import Response as OpenAPIResponse
from expanse.schematic.support.extensions.operations.extension import OperationExtension


if TYPE_CHECKING:
    from expanse.schematic.openapi.operation import Operation
    from expanse.schematic.support.route_info import RouteInfo


class ValidationError(BaseModel):
    loc: list[str] = Field(..., description="Location of the validation error")
    msg: str = Field(
        ..., description="The complete error message of the validation error"
    )
    type: str = Field(..., description="The type of validation error")


class ResponseExtension(OperationExtension):
    """
    Extension to detect and add responses.

    It does not handle error responses.
    """

    def handle(self, operation: Operation, route_info: RouteInfo) -> None:
        # Try to find explicit response codes first
        doc_string = route_info.doc_string

        description = doc_string.returns
        success_response = OpenAPIResponse(description)
        if (
            route_info.signature.return_annotation
            and route_info.signature.return_annotation != NoneType
        ):
            # Skip Response type itself
            from expanse.http.response import Response as HttpResponse

            if route_info.signature.return_annotation != HttpResponse:
                schema = self._schema_registry.generate_from_type(
                    route_info.signature.return_annotation
                )
                media_type = MediaType(schema)
                success_response.add_content("application/json", media_type)
                operation.responses.add_response("200", success_response)

        inference = self._inference.infer(route_info)
        for inferred_response in inference.responses:
            if not operation.responses.has_response(str(inferred_response.status_code)):
                if 200 <= inferred_response.status_code < 300:
                    response = success_response
                else:
                    response = OpenAPIResponse("")

                if inferred_response.content_type is not None:
                    response.add_content(inferred_response.content_type, MediaType())

                operation.responses.add_response(
                    str(inferred_response.status_code), response
                )

        if operation.responses.is_empty():
            operation.responses.add_response("200", success_response)

        # Add validation error response if needed
        if not operation.responses.has_response("422") and operation.request_body:
            validation_error_response = OpenAPIResponse("Validation Error")
            reference, _ = self._schema_registry.get_or_create_component_schema(
                ValidationError
            )
            media_type = MediaType(reference)
            validation_error_response.add_content("application/json", media_type)
            operation.responses.add_response("422", validation_error_response)
