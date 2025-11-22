from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.schematic.openapi.callback import Callback
    from expanse.schematic.openapi.example import Example
    from expanse.schematic.openapi.header import Header
    from expanse.schematic.openapi.link import Link
    from expanse.schematic.openapi.parameter import Parameter
    from expanse.schematic.openapi.path_item import PathItem
    from expanse.schematic.openapi.reference import Reference
    from expanse.schematic.openapi.request_body import RequestBody
    from expanse.schematic.openapi.response import Response
    from expanse.schematic.openapi.schema import Schema
    from expanse.schematic.openapi.security_scheme import SecurityScheme


class Components:
    def __init__(self) -> None:
        self.schemas: dict[str, Schema] = {}
        self.responses: dict[str, Response | Reference] = {}
        self.parameters: dict[str, Parameter | Reference] = {}
        self.examples: dict[str, Example | Reference] = {}
        self.request_bodies: dict[str, RequestBody | Reference] = {}
        self.headers: dict[str, Header | Reference] = {}
        self.security_schemes: dict[str, SecurityScheme | Reference] = {}
        self.links: dict[str, Link | Reference] = {}
        self.callbacks: dict[str, Callback | Reference] = {}
        self.path_items: dict[str, PathItem | Reference] = {}

    def add_schema(self, name: str, schema: Schema) -> Components:
        self.schemas[name] = schema
        return self

    def add_response(self, name: str, response: Response | Reference) -> Components:
        self.responses[name] = response
        return self

    def add_parameter(self, name: str, parameter: Parameter | Reference) -> Components:
        self.parameters[name] = parameter
        return self

    def add_example(self, name: str, example: Example | Reference) -> Components:
        self.examples[name] = example
        return self

    def add_request_body(
        self, name: str, request_body: RequestBody | Reference
    ) -> Components:
        self.request_bodies[name] = request_body
        return self

    def add_header(self, name: str, header: Header | Reference) -> Components:
        self.headers[name] = header
        return self

    def add_security_scheme(
        self, name: str, security_scheme: SecurityScheme | Reference
    ) -> Components:
        self.security_schemes[name] = security_scheme
        return self

    def add_link(self, name: str, link: Link | Reference) -> Components:
        self.links[name] = link
        return self

    def add_callback(self, name: str, callback: Callback | Reference) -> Components:
        self.callbacks[name] = callback
        return self

    def add_path_item(self, name: str, path_item: PathItem | Reference) -> Components:
        self.path_items[name] = path_item
        return self

    def is_empty(self) -> bool:
        return (
            not self.schemas
            and not self.responses
            and not self.parameters
            and not self.examples
            and not self.request_bodies
            and not self.headers
            and not self.security_schemes
            and not self.links
            and not self.callbacks
            and not self.path_items
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}

        if self.schemas:
            result["schemas"] = {
                name: schema.to_dict() for name, schema in self.schemas.items()
            }

        if self.responses:
            result["responses"] = {
                name: response.to_dict() for name, response in self.responses.items()
            }

        if self.parameters:
            result["parameters"] = {
                name: parameter.to_dict() for name, parameter in self.parameters.items()
            }

        if self.examples:
            result["examples"] = {
                name: example.to_dict() for name, example in self.examples.items()
            }

        if self.request_bodies:
            result["requestBodies"] = {
                name: rb.to_dict() for name, rb in self.request_bodies.items()
            }

        if self.headers:
            result["headers"] = {
                name: header.to_dict() for name, header in self.headers.items()
            }

        if self.security_schemes:
            result["securitySchemes"] = {
                name: ss.to_dict() for name, ss in self.security_schemes.items()
            }

        if self.links:
            result["links"] = {
                name: link.to_dict() for name, link in self.links.items()
            }

        if self.callbacks:
            result["callbacks"] = {
                name: callback.to_dict() for name, callback in self.callbacks.items()
            }

        if self.path_items:
            result["pathItems"] = {
                name: pi.to_dict() for name, pi in self.path_items.items()
            }

        return result
