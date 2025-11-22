from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.schematic.openapi.server import Server


class Link:
    def __init__(
        self,
        operation_ref: str | None = None,
        operation_id: str | None = None,
    ) -> None:
        if operation_ref is not None and operation_id is not None:
            raise ValueError("operation_ref and operation_id are mutually exclusive")

        if operation_ref is None and operation_id is None:
            raise ValueError("Either operation_ref or operation_id must be provided")

        self.operation_ref: str | None = operation_ref
        self.operation_id: str | None = operation_id
        self.parameters: dict[str, Any] = {}
        self.request_body: Any = None
        self.description: str | None = None
        self.server: Server | None = None

    def set_description(self, description: str) -> Link:
        self.description = description
        return self

    def add_parameter(self, name: str, value: Any) -> Link:
        self.parameters[name] = value
        return self

    def set_parameters(self, parameters: dict[str, Any]) -> Link:
        self.parameters = parameters
        return self

    def set_request_body(self, request_body: Any) -> Link:
        self.request_body = request_body
        return self

    def set_server(self, server: Server) -> Link:
        self.server = server
        return self

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if self.operation_ref is not None:
            result["operationRef"] = self.operation_ref

        if self.operation_id is not None:
            result["operationId"] = self.operation_id

        if self.parameters:
            result["parameters"] = self.parameters

        if self.request_body is not None:
            result["requestBody"] = self.request_body

        if self.description is not None:
            result["description"] = self.description

        if self.server is not None:
            result["server"] = self.server.to_dict()

        return result
