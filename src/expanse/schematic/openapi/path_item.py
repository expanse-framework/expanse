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
    """

    def __init__(self, ref: str | None = None) -> None:
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
        self.summary = summary
        return self

    def set_description(self, description: str) -> PathItem:
        self.description = description
        return self

    def set_get(self, operation: Operation) -> PathItem:
        self.get = operation
        return self

    def set_put(self, operation: Operation) -> PathItem:
        self.put = operation
        return self

    def set_post(self, operation: Operation) -> PathItem:
        self.post = operation
        return self

    def set_delete(self, operation: Operation) -> PathItem:
        self.delete = operation
        return self

    def set_options(self, operation: Operation) -> PathItem:
        self.options = operation
        return self

    def set_head(self, operation: Operation) -> PathItem:
        self.head = operation
        return self

    def set_patch(self, operation: Operation) -> PathItem:
        self.patch = operation
        return self

    def set_trace(self, operation: Operation) -> PathItem:
        self.trace = operation
        return self

    def add_server(self, server: Server) -> PathItem:
        self.servers.append(server)
        return self

    def add_parameter(self, parameter: Parameter | Reference) -> PathItem:
        self.parameters.append(parameter)
        return self

    def to_dict(self) -> dict[str, Any]:
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
