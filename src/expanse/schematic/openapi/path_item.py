from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.schematic.openapi.operation import Operation
    from expanse.schematic.openapi.parameter import Parameter
    from expanse.schematic.openapi.reference import Reference
    from expanse.schematic.openapi.server import Server


class PathItem:
    """
    Describes the operations available on a single path.
    A Path Item MAY be empty, due to ACL constraints.
    The path itself is still exposed to the documentation viewer but they will not know
    which operations and parameters are available.
    """

    def __init__(self, ref: str | None = None) -> None:
        """
        Initialize a PathItem object.

        Args:
            ref: Allows for a referenced definition of this path item.
                The referenced structure MUST be in the form of a Path Item Object.
        """
        self.ref: str | None = ref
        self.summary: str | None = None
        self.description: str | None = None
        self.get: Operation | None = None
        self.put: Operation | None = None
        self.post: Operation | None = None
        self.delete: Operation | None = None
        self.options: Operation | None = None
        self.head: Operation | None = None
        self.patch: Operation | None = None
        self.trace: Operation | None = None
        self.servers: list[Server] = []
        self.parameters: list[Parameter | Reference] = []

    def set_summary(self, summary: str) -> PathItem:
        """
        Set an optional string summary, intended to apply to all operations in this path.

        Args:
            summary: A string summary intended to apply to all operations in this path.

        Returns:
            Self for method chaining
        """
        self.summary = summary
        return self

    def set_description(self, description: str) -> PathItem:
        """
        Set an optional string description, intended to apply to all operations in this path.

        Args:
            description: A string description intended to apply to all operations in this path.
                        CommonMark syntax MAY be used for rich text representation.

        Returns:
            Self for method chaining
        """
        self.description = description
        return self

    def set_get(self, operation: Operation) -> PathItem:
        """
        Set a definition of a GET operation on this path.

        Args:
            operation: A definition of a GET operation on this path.

        Returns:
            Self for method chaining
        """
        self.get = operation
        return self

    def set_put(self, operation: Operation) -> PathItem:
        """
        Set a definition of a PUT operation on this path.

        Args:
            operation: A definition of a PUT operation on this path.

        Returns:
            Self for method chaining
        """
        self.put = operation
        return self

    def set_post(self, operation: Operation) -> PathItem:
        """
        Set a definition of a POST operation on this path.

        Args:
            operation: A definition of a POST operation on this path.

        Returns:
            Self for method chaining
        """
        self.post = operation
        return self

    def set_delete(self, operation: Operation) -> PathItem:
        """
        Set a definition of a DELETE operation on this path.

        Args:
            operation: A definition of a DELETE operation on this path.

        Returns:
            Self for method chaining
        """
        self.delete = operation
        return self

    def set_options(self, operation: Operation) -> PathItem:
        """
        Set a definition of an OPTIONS operation on this path.

        Args:
            operation: A definition of an OPTIONS operation on this path.

        Returns:
            Self for method chaining
        """
        self.options = operation
        return self

    def set_head(self, operation: Operation) -> PathItem:
        """
        Set a definition of a HEAD operation on this path.

        Args:
            operation: A definition of a HEAD operation on this path.

        Returns:
            Self for method chaining
        """
        self.head = operation
        return self

    def set_patch(self, operation: Operation) -> PathItem:
        """
        Set a definition of a PATCH operation on this path.

        Args:
            operation: A definition of a PATCH operation on this path.

        Returns:
            Self for method chaining
        """
        self.patch = operation
        return self

    def set_trace(self, operation: Operation) -> PathItem:
        """
        Set a definition of a TRACE operation on this path.

        Args:
            operation: A definition of a TRACE operation on this path.

        Returns:
            Self for method chaining
        """
        self.trace = operation
        return self

    def add_server(self, server: Server) -> PathItem:
        """
        Add an alternative server to service all operations in this path.

        Args:
            server: A server object

        Returns:
            Self for method chaining
        """
        self.servers.append(server)
        return self

    def add_parameter(self, parameter: Parameter | Reference) -> PathItem:
        """
        Add a parameter that is applicable for all the operations described under this path.

        Args:
            parameter: A parameter object or reference. These parameters can be overridden
                      at the operation level, but cannot be removed there.

        Returns:
            Self for method chaining
        """
        self.parameters.append(parameter)
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the PathItem object to a dictionary representation."""
        result: dict[str, Any] = {}

        if self.ref is not None:
            result["$ref"] = self.ref

        if self.summary is not None:
            result["summary"] = self.summary

        if self.description is not None:
            result["description"] = self.description

        if self.get is not None:
            result["get"] = self.get.to_dict()

        if self.put is not None:
            result["put"] = self.put.to_dict()

        if self.post is not None:
            result["post"] = self.post.to_dict()

        if self.delete is not None:
            result["delete"] = self.delete.to_dict()

        if self.options is not None:
            result["options"] = self.options.to_dict()

        if self.head is not None:
            result["head"] = self.head.to_dict()

        if self.patch is not None:
            result["patch"] = self.patch.to_dict()

        if self.trace is not None:
            result["trace"] = self.trace.to_dict()

        if self.servers:
            result["servers"] = [server.to_dict() for server in self.servers]

        if self.parameters:
            result["parameters"] = [param.to_dict() for param in self.parameters]

        return result

    def __repr__(self) -> str:
        operations = []
        if self.get:
            operations.append("GET")
        if self.post:
            operations.append("POST")
        if self.put:
            operations.append("PUT")
        if self.delete:
            operations.append("DELETE")
        if self.patch:
            operations.append("PATCH")
        if self.options:
            operations.append("OPTIONS")
        if self.head:
            operations.append("HEAD")
        if self.trace:
            operations.append("TRACE")

        if operations:
            return f"PathItem({', '.join(operations)})"
        else:
            return "PathItem(no operations)"
