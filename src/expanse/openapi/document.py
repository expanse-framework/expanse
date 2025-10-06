from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.openapi.config import OpenAPIConfig


class OpenAPIDocument:
    """Represents an OpenAPI specification document."""

    def __init__(self, config: OpenAPIConfig) -> None:
        """Initialize OpenAPI document with configuration."""

        self.config = config
        self.paths: dict[str, dict[str, Any]] = {}
        self.components: dict[str, Any] = {
            "schemas": {},
            "responses": {},
            "parameters": {},
            "examples": {},
            "requestBodies": {},
            "headers": {},
            "securitySchemes": config.security_schemes.copy(),
            "links": {},
            "callbacks": {},
        }
        self.tags: list[dict[str, Any]] = config.tags.copy()
        self.external_docs: dict[str, Any] | None = None

    def add_path(self, path: str, method: str, operation: dict[str, Any]) -> None:
        """Add a path operation to the document."""
        if path not in self.paths:
            self.paths[path] = {}
        self.paths[path][method.lower()] = operation

    def add_schema(self, name: str, schema: dict[str, Any]) -> None:
        """Add a schema to the components section."""
        self.components["schemas"][name] = schema

    def add_response(self, name: str, response: dict[str, Any]) -> None:
        """Add a response to the components section."""
        self.components["responses"][name] = response

    def add_parameter(self, name: str, parameter: dict[str, Any]) -> None:
        """Add a parameter to the components section."""
        self.components["parameters"][name] = parameter

    def add_request_body(self, name: str, request_body: dict[str, Any]) -> None:
        """Add a request body to the components section."""
        self.components["requestBodies"][name] = request_body

    def add_tag(self, name: str, description: str | None = None) -> None:
        """Add a tag definition."""
        tag = {"name": name}
        if description:
            tag["description"] = description

        # Avoid duplicates
        for existing_tag in self.tags:
            if existing_tag["name"] == name:
                return

        self.tags.append(tag)

    def to_dict(self) -> dict[str, Any]:
        """Convert the document to a dictionary representation."""
        doc = {
            "openapi": self.config.openapi_version,
            "info": {
                "title": self.config.title,
                "version": self.config.version,
            },
            "paths": self.paths,
        }

        if self.config.description:
            doc["info"]["description"] = self.config.description

        if self.config.contact:
            doc["info"]["contact"] = self.config.contact

        if self.config.license_info:
            doc["info"]["license"] = self.config.license_info

        if self.config.terms_of_service:
            doc["info"]["termsOfService"] = self.config.terms_of_service

        if self.config.servers:
            doc["servers"] = self.config.servers

        if self.tags:
            doc["tags"] = self.tags

        if self.external_docs:
            doc["externalDocs"] = self.external_docs

        # Only include components if they have content
        if any(self.components.values()):
            doc["components"] = {k: v for k, v in self.components.items() if v}

        return doc

    def to_json(self, indent: int | None = 2) -> str:
        """Convert the document to JSON string."""
        import json

        return json.dumps(self.to_dict(), indent=indent)

    def to_yaml(self) -> str:
        """Convert the document to YAML string."""
        try:
            import yaml

            return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)
        except ImportError:
            raise ImportError(
                "PyYAML is required for YAML export. Install with: pip install pyyaml"
            )


class PathItem:
    """Represents a path item in OpenAPI specification."""

    def __init__(self, path: str) -> None:
        """Initialize path item."""
        self.path = path
        self.operations: dict[str, Operation] = {}
        self.parameters: list[dict[str, Any]] = []
        self.summary: str | None = None
        self.description: str | None = None

    def add_operation(self, method: str, operation: Operation) -> None:
        """Add an operation to this path."""
        self.operations[method.lower()] = operation

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result: dict[str, Any] = {}

        if self.summary:
            result["summary"] = self.summary

        if self.description:
            result["description"] = self.description

        if self.parameters:
            result["parameters"] = self.parameters

        for method, operation in self.operations.items():
            result[method] = operation.to_dict()

        return result


class Operation:
    """Represents an operation in OpenAPI specification."""

    def __init__(
        self,
        method: str,
        path: str,
        operation_id: str | None = None,
    ) -> None:
        """Initialize operation."""
        self.method = method.upper()
        self.path = path
        self.operation_id = (
            operation_id
            or f"{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}"
        )
        self.summary: str | None = None
        self.description: str | None = None
        self.tags: list[str] = []
        self.parameters: list[dict[str, Any]] = []
        self.request_body: dict[str, Any] | None = None
        self.responses: dict[str, dict[str, Any]] = {}
        self.security: list[dict[str, Any]] = []
        self.deprecated: bool = False

    def add_parameter(
        self,
        name: str,
        param_in: str,
        schema: dict[str, Any],
        required: bool = False,
        description: str | None = None,
    ) -> None:
        """Add a parameter to the operation."""
        param = {
            "name": name,
            "in": param_in,
            "required": required,
            "schema": schema,
        }
        if description:
            param["description"] = description

        self.parameters.append(param)

    def add_response(
        self,
        status_code: str | int,
        description: str,
        content: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
    ) -> None:
        """Add a response to the operation."""
        response = {"description": description}

        if content:
            response["content"] = content

        if headers:
            response["headers"] = headers

        self.responses[str(status_code)] = response

    def set_request_body(
        self,
        content: dict[str, Any],
        description: str | None = None,
        required: bool = True,
    ) -> None:
        """Set the request body for the operation."""
        self.request_body = {
            "content": content,
            "required": required,
        }
        if description:
            self.request_body["description"] = description

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "operationId": self.operation_id,
            "responses": self.responses or {"200": {"description": "Success"}},
        }

        if self.summary:
            result["summary"] = self.summary

        if self.description:
            result["description"] = self.description

        if self.tags:
            result["tags"] = self.tags

        if self.parameters:
            result["parameters"] = self.parameters

        if self.request_body:
            result["requestBody"] = self.request_body

        if self.security:
            result["security"] = self.security

        if self.deprecated:
            result["deprecated"] = self.deprecated

        return result
