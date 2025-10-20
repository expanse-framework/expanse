from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Self


if TYPE_CHECKING:
    from expanse.schematic.openapi.callback import Callback
    from expanse.schematic.openapi.parameter import Parameter
    from expanse.schematic.openapi.reference import Reference
    from expanse.schematic.openapi.request_body import RequestBody
    from expanse.schematic.openapi.responses import Responses
    from expanse.schematic.openapi.security_requirement import SecurityRequirement
    from expanse.schematic.openapi.server import Server
    from expanse.schematic.openapi.tag import ExternalDocumentation


class Operation:
    """
    Describes a single API operation on a path.
    """

    def __init__(self, method: str):
        from expanse.schematic.openapi.responses import Responses

        self.operation_id: str | None = None
        self.method: str = method
        self.path: str = ""
        self.description: str = ""
        self.summary: str = ""
        self.deprecated: bool = False
        self.tags: list[str] = []
        self.parameters: list[Parameter | Reference] = []
        self.request_body: RequestBody | Reference | None = None
        self.responses: Responses = Responses()
        self.callbacks: dict[str, Callback | Reference] = {}
        self.security: list[SecurityRequirement] = []
        self.servers: list[Server] = []
        self.external_docs: ExternalDocumentation | None = None

    def set_operation_id(self, operation_id: str) -> Self:
        """
        Set the unique string used to identify the operation.

        Args:
            operation_id: Unique string used to identify the operation

        Returns:
            Self for method chaining
        """
        self.operation_id = operation_id
        return self

    def set_summary(self, summary: str) -> Self:
        """
        Set a short summary of what the operation does.

        Args:
            summary: A short summary of what the operation does

        Returns:
            Self for method chaining
        """
        self.summary = summary
        return self

    def set_description(self, description: str) -> Self:
        """
        Set a verbose explanation of the operation behavior.

        Args:
            description: A verbose explanation of the operation behavior

        Returns:
            Self for method chaining
        """
        self.description = description
        return self

    def set_deprecated(self, deprecated: bool) -> Self:
        """
        Set whether this operation is deprecated.

        Args:
            deprecated: Declares this operation to be deprecated

        Returns:
            Self for method chaining
        """
        self.deprecated = deprecated
        return self

    def add_tag(self, tag: str) -> Self:
        """
        Add a tag for API documentation control.

        Args:
            tag: A tag for API documentation control

        Returns:
            Self for method chaining
        """
        self.tags.append(tag)
        return self

    def add_parameter(self, parameter: Parameter | Reference) -> Self:
        """
        Add a parameter that is applicable for this operation.

        Args:
            parameter: A parameter object or reference

        Returns:
            Self for method chaining
        """
        self.parameters.append(parameter)
        return self

    def set_request_body(self, request_body: RequestBody | Reference) -> Self:
        """
        Set the request body applicable for this operation.

        Args:
            request_body: The request body object or reference

        Returns:
            Self for method chaining
        """
        self.request_body = request_body
        return self

    def set_responses(self, responses: Responses) -> Self:
        """
        Set the list of possible responses as they are returned from executing this operation.

        Args:
            responses: The responses object

        Returns:
            Self for method chaining
        """
        self.responses = responses
        return self

    def add_callback(self, name: str, callback: Callback | Reference) -> Self:
        """
        Add a callback related to the parent operation.

        Args:
            name: A unique identifier for the callback
            callback: The callback object or reference

        Returns:
            Self for method chaining
        """
        self.callbacks[name] = callback
        return self

    def add_security_requirement(self, requirement: SecurityRequirement) -> Self:
        """
        Add a security requirement for this operation.

        Args:
            requirement: A security requirement object

        Returns:
            Self for method chaining
        """
        self.security.append(requirement)
        return self

    def add_server(self, server: Server) -> Self:
        """
        Add an alternative server to service this operation.

        Args:
            server: A server object

        Returns:
            Self for method chaining
        """
        self.servers.append(server)
        return self

    def set_external_docs(self, external_docs: ExternalDocumentation) -> Self:
        """
        Set additional external documentation for this operation.

        Args:
            external_docs: Additional external documentation

        Returns:
            Self for method chaining
        """
        self.external_docs = external_docs
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the Operation object to a dictionary representation."""
        result: dict[str, Any] = {}

        if self.tags:
            result["tags"] = self.tags

        if self.summary:
            result["summary"] = self.summary

        if self.description:
            result["description"] = self.description

        if self.external_docs is not None:
            result["externalDocs"] = self.external_docs.to_dict()

        if self.operation_id is not None:
            result["operationId"] = self.operation_id

        if self.parameters:
            result["parameters"] = [param.to_dict() for param in self.parameters]

        if self.request_body is not None:
            result["requestBody"] = self.request_body.to_dict()

        if not self.responses.is_empty():
            result["responses"] = self.responses.to_dict()

        if self.callbacks:
            result["callbacks"] = {
                name: callback.to_dict() for name, callback in self.callbacks.items()
            }

        if self.deprecated:
            result["deprecated"] = self.deprecated

        if self.security:
            result["security"] = [req.to_dict() for req in self.security]

        if self.servers:
            result["servers"] = [server.to_dict() for server in self.servers]

        return result

    def __repr__(self) -> str:
        return f"Operation(method='{self.method}', operation_id='{self.operation_id}')"
