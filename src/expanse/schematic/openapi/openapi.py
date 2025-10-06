from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from expanse.schematic.openapi.info import Info


if TYPE_CHECKING:
    from expanse.schematic.openapi.components import Components
    from expanse.schematic.openapi.path_item import PathItem
    from expanse.schematic.openapi.paths import Paths
    from expanse.schematic.openapi.reference import Reference
    from expanse.schematic.openapi.security_requirement import SecurityRequirement
    from expanse.schematic.openapi.server import Server
    from expanse.schematic.openapi.tag import ExternalDocumentation
    from expanse.schematic.openapi.tag import Tag


class OpenAPI:
    """
    This is the root object of the OpenAPI document.
    """

    def __init__(self, version: str, info: Info) -> None:
        """
        Initialize an OpenAPI document object.

        Args:
            openapi: This string MUST be the version number of the OpenAPI Specification
                    that the OpenAPI document uses. The openapi field SHOULD be used by
                    tooling to interpret the OpenAPI document.
            info: Provides metadata about the API. The metadata MAY be used by tooling as required.
        """
        self.version: str = version
        self.info: Info = info
        self.json_schema_dialect: str | None = None
        self.servers: list[Server] = []
        self.paths: Paths | None = None
        self.webhooks: dict[str, PathItem | Reference] = {}
        self.components: Components | None = None
        self.security: list[SecurityRequirement] = []
        self.tags: list[Tag] = []
        self.external_docs: ExternalDocumentation | None = None
        self.description: str = ""

    def set_description(self, description: str) -> OpenAPI:
        """
        Set the description of the API.

        Args:
            description: A short description of the API. CommonMark syntax MAY be used for rich text representation.

        Returns:
            Self for method chaining
        """
        self.description = description
        return self

    def set_json_schema_dialect(self, dialect: str) -> OpenAPI:
        """
        Set the default value for the $schema keyword within Schema Objects.

        Args:
            dialect: The default value for the $schema keyword within Schema Objects
                    contained within this OAS document. This MUST be in the form of a URI.

        Returns:
            Self for method chaining
        """
        self.json_schema_dialect = dialect
        return self

    def add_server(self, server: Server) -> OpenAPI:
        """
        Add a server to the list of servers.

        Args:
            server: A Server Object, which provides connectivity information to a target server.

        Returns:
            Self for method chaining
        """
        self.servers.append(server)
        return self

    def set_servers(self, servers: list[Server]) -> OpenAPI:
        """
        Set the servers array.

        Args:
            servers: An array of Server Objects, which provide connectivity information
                    to a target server. If the servers property is not provided, or is an empty array,
                    the default value would be a Server Object with a url value of /.

        Returns:
            Self for method chaining
        """
        self.servers = servers
        return self

    def set_paths(self, paths: Paths) -> OpenAPI:
        """
        Set the available paths and operations for the API.

        Args:
            paths: The available paths and operations for the API.

        Returns:
            Self for method chaining
        """
        self.paths = paths
        return self

    def add_webhook(self, name: str, webhook: PathItem | Reference) -> OpenAPI:
        """
        Add a webhook that MAY be received as part of this API.

        Args:
            name: A unique string to refer to the webhook
            webhook: A Path Item Object that describes a request that may be initiated
                    by the API provider and the expected responses.

        Returns:
            Self for method chaining
        """
        self.webhooks[name] = webhook
        return self

    def set_components(self, components: Components) -> OpenAPI:
        """
        Set the components object.

        Args:
            components: An element to hold various schemas for the document.

        Returns:
            Self for method chaining
        """
        self.components = components
        return self

    def add_security_requirement(self, requirement: SecurityRequirement) -> OpenAPI:
        """
        Add a security requirement.

        Args:
            requirement: A security requirement object that can be used across the API.

        Returns:
            Self for method chaining
        """
        self.security.append(requirement)
        return self

    def set_security(self, security: list[SecurityRequirement]) -> OpenAPI:
        """
        Set the security requirements.

        Args:
            security: A declaration of which security mechanisms can be used across the API.
                     The list of values includes alternative security requirement objects that can be used.
                     Only one of the security requirement objects need to be satisfied to authorize a request.

        Returns:
            Self for method chaining
        """
        self.security = security
        return self

    def add_tag(self, tag: Tag) -> OpenAPI:
        """
        Add a tag to the document.

        Args:
            tag: A tag used by the document with additional metadata.

        Returns:
            Self for method chaining
        """
        self.tags.append(tag)
        return self

    def set_tags(self, tags: list[Tag]) -> OpenAPI:
        """
        Set the tags for the document.

        Args:
            tags: A list of tags used by the document with additional metadata.
                 The order of the tags can be used to reflect on their order by the parsing tools.

        Returns:
            Self for method chaining
        """
        self.tags = tags
        return self

    def set_external_docs(self, external_docs: ExternalDocumentation) -> OpenAPI:
        """
        Set additional external documentation.

        Args:
            external_docs: Additional external documentation.

        Returns:
            Self for method chaining
        """
        self.external_docs = external_docs
        return self

    def set_info(self, info: Info) -> OpenAPI:
        """
        Set the metadata about the API.

        Args:
            info: The metadata about the API.

        Returns:
            Self for method chaining
        """
        self.info = info
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the OpenAPI object to a dictionary representation."""
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

        if self.components is not None:
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
