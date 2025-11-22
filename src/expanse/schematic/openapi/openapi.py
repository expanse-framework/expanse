from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from expanse.schematic.openapi.components import Components


if TYPE_CHECKING:
    from expanse.schematic.openapi.info import Info
    from expanse.schematic.openapi.path_item import PathItem
    from expanse.schematic.openapi.paths import Paths
    from expanse.schematic.openapi.reference import Reference
    from expanse.schematic.openapi.security_requirement import SecurityRequirement
    from expanse.schematic.openapi.server import Server
    from expanse.schematic.openapi.tag import ExternalDocumentation
    from expanse.schematic.openapi.tag import Tag


class OpenAPI:
    """
    The OpenAPI document.
    """

    def __init__(self, version: str, info: Info) -> None:
        self.version: str = version
        self.info: Info = info
        self.json_schema_dialect: str | None = None
        self.servers: list[Server] = []
        self.paths: Paths | None = None
        self.webhooks: dict[str, PathItem | Reference] = {}
        self.components: Components = Components()
        self.security: list[SecurityRequirement] = []
        self.tags: list[Tag] = []
        self.external_docs: ExternalDocumentation | None = None
        self.description: str = ""

    def set_description(self, description: str) -> OpenAPI:
        self.description = description
        return self

    def set_json_schema_dialect(self, dialect: str) -> OpenAPI:
        self.json_schema_dialect = dialect
        return self

    def add_server(self, server: Server) -> OpenAPI:
        self.servers.append(server)
        return self

    def set_servers(self, servers: list[Server]) -> OpenAPI:
        self.servers = servers
        return self

    def set_paths(self, paths: Paths) -> OpenAPI:
        self.paths = paths
        return self

    def add_webhook(self, name: str, webhook: PathItem | Reference) -> OpenAPI:
        self.webhooks[name] = webhook
        return self

    def set_components(self, components: Components) -> OpenAPI:
        self.components = components

        return self

    def add_security_requirement(self, requirement: SecurityRequirement) -> OpenAPI:
        self.security.append(requirement)

        return self

    def set_security(self, security: list[SecurityRequirement]) -> OpenAPI:
        self.security = security

        return self

    def add_tag(self, tag: Tag) -> OpenAPI:
        self.tags.append(tag)

        return self

    def set_tags(self, tags: list[Tag]) -> OpenAPI:
        self.tags = tags

        return self

    def set_external_docs(self, external_docs: ExternalDocumentation) -> OpenAPI:
        self.external_docs = external_docs

        return self

    def set_info(self, info: Info) -> OpenAPI:
        self.info = info

        return self

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "openapi": self.version,
            "info": self.info.to_dict(),
        }

        if self.json_schema_dialect is not None:
            result["jsonSchemaDialect"] = self.json_schema_dialect

        if self.servers:
            result["servers"] = [server.to_dict() for server in self.servers]

        if self.paths is not None:
            result["paths"] = self.paths.to_dict()

        if self.webhooks:
            result["webhooks"] = {
                name: webhook.to_dict() for name, webhook in self.webhooks.items()
            }

        if not self.components.is_empty():
            result["components"] = self.components.to_dict()

        if self.security:
            result["security"] = [req.to_dict() for req in self.security]

        if self.tags:
            result["tags"] = [tag.to_dict() for tag in self.tags]

        if self.external_docs is not None:
            result["externalDocs"] = self.external_docs.to_dict()

        return result

    def __repr__(self) -> str:
        return f"OpenAPI(version='{self.version}', title='{self.info.title}')"
