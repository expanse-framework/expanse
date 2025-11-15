from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.schematic.openapi.reference import Reference
from expanse.schematic.openapi.response import Response as OpenAPIResponse
from expanse.schematic.support.extensions.operations.extension import OperationExtension


if TYPE_CHECKING:
    from expanse.schematic.openapi.operation import Operation
    from expanse.schematic.support.route_info import RouteInfo


class ErrorResponseExtension(OperationExtension):
    """
    Extension to detect and add error responses.
    """

    def handle(self, operation: Operation, route_info: RouteInfo) -> None:
        signature_info = route_info.signature
        body_param = signature_info.body_parameter

        if (
            body_param
            and body_param.pydantic_model
            and not operation.responses.has_response("422")
        ):
            # If the body parameter is a Pydantic model, any validation error will lead to a 422 response.
            operation.responses.add_response(
                "422",
                OpenAPIResponse("Validation Error"),
            )

        inference = self._inference.infer(route_info)
        for inferred_error in inference.errors:
            if not operation.responses.has_response(str(inferred_error.status_code)):
                operation.responses.add_response(
                    str(inferred_error.status_code),
                    OpenAPIResponse(inferred_error.description),
                )
        for error in route_info.doc_string.raises:
            status_code = str(error.status_code)
            description = error.description or "Error Response"
            if not operation.responses.has_response(status_code):
                error_response = OpenAPIResponse(description)
                operation.responses.add_response(status_code, error_response)
                continue

            reponse = operation.responses.get_response(status_code)
            assert isinstance(reponse, OpenAPIResponse | Reference)
            reponse.description = description
