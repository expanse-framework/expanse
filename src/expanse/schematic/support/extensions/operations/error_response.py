from __future__ import annotations

from typing import TYPE_CHECKING

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
        # Try to find explicit response codes first
        doc_string = route_info.doc_string
        print(doc_string)

        for error in route_info.doc_string.raises:
            status_code = str(error.status_code)
            description = error.description or "Error Response"
            error_response = OpenAPIResponse(description)
            operation.responses.add_response(status_code, error_response)

        inference = self._inference.infer(route_info)
        for inferred_error in inference.errors:
            if not operation.responses.has_response(str(inferred_error.status_code)):
                operation.responses.add_response(
                    str(inferred_error.status_code),
                    OpenAPIResponse(inferred_error.description),
                )
