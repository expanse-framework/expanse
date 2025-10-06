from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.schematic.openapi.server import Server


class Link:
    """
    The Link object represents a possible design-time link for a response.
    The presence of a link does not guarantee the caller's ability to successfully invoke it,
    rather it provides a known relationship and traversal mechanism between responses and other operations.
    """

    def __init__(
        self,
        operation_ref: str | None = None,
        operation_id: str | None = None,
    ) -> None:
        """
        Initialize a Link object.

        Args:
            operation_ref: A relative or absolute URI reference to an OAS operation.
                          This field is mutually exclusive of the operation_id field.
            operation_id: The name of an existing, resolvable OAS operation, as defined
                         with a unique operationId. This field is mutually exclusive of
                         the operation_ref field.
        """
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

    def set_description(self, description: str) -> "Link":
        """
        Set a description of the link.

        Args:
            description: A description of the link. CommonMark syntax MAY be used
                        for rich text representation.

        Returns:
            Self for method chaining
        """
        self.description = description
        return self

    def add_parameter(self, name: str, value: Any) -> "Link":
        """
        Add a parameter to pass to the linked operation.

        Args:
            name: The parameter name to be used
            value: A constant or an expression to be evaluated and passed to the linked operation

        Returns:
            Self for method chaining
        """
        self.parameters[name] = value
        return self

    def set_parameters(self, parameters: dict[str, Any]) -> "Link":
        """
        Set parameters to pass to the linked operation.

        Args:
            parameters: A map representing parameters to pass to an operation.
                       The key is the parameter name to be used, whereas the value
                       can be a constant or an expression to be evaluated.

        Returns:
            Self for method chaining
        """
        self.parameters = parameters
        return self

    def set_request_body(self, request_body: Any) -> "Link":
        """
        Set a literal value or expression to use as a request body when calling the target operation.

        Args:
            request_body: A literal value or expression to use as a request body

        Returns:
            Self for method chaining
        """
        self.request_body = request_body
        return self

    def set_server(self, server: "Server") -> "Link":
        """
        Set a server object to be used by the target operation.

        Args:
            server: A server object to be used by the target operation

        Returns:
            Self for method chaining
        """
        self.server = server
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the Link object to a dictionary representation."""
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

    def __repr__(self) -> str:
        if self.operation_ref:
            return f"Link(operation_ref='{self.operation_ref}')"
        else:
            return f"Link(operation_id='{self.operation_id}')"
