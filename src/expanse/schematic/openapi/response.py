from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.schematic.openapi.header import Header
    from expanse.schematic.openapi.link import Link
    from expanse.schematic.openapi.media_type import MediaType
    from expanse.schematic.openapi.reference import Reference


class Response:
    """
    Describes a single response from an API Operation, including design-time,
    static links to operations based on the response.
    """

    def __init__(self, description: str) -> None:
        """
        Initialize a Response object.

        Args:
            description: A description of the response. CommonMark syntax MAY be used
                        for rich text representation.
        """
        self.description: str = description
        self.headers: dict[str, Header | Reference] = {}
        self.content: dict[str, MediaType] = {}
        self.links: dict[str, Link | Reference] = {}

    def add_header(self, name: str, header: "Header | Reference") -> "Response":
        """
        Add a header to the response.

        Args:
            name: The header name
            header: The header definition or reference

        Returns:
            Self for method chaining
        """
        self.headers[name] = header
        return self

    def add_content(self, media_type: str, content: "MediaType") -> "Response":
        """
        Add content description for a specific media type.

        Args:
            media_type: The media type (e.g., 'application/json')
            content: The media type object describing the content

        Returns:
            Self for method chaining
        """
        self.content[media_type] = content
        return self

    def add_link(self, name: str, link: "Link | Reference") -> "Response":
        """
        Add a link to the response.

        Args:
            name: The link name
            link: The link definition or reference

        Returns:
            Self for method chaining
        """
        self.links[name] = link
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the Response object to a dictionary representation."""
        result: dict[str, Any] = {"description": self.description}

        if self.headers:
            result["headers"] = {
                name: header.to_dict() for name, header in self.headers.items()
            }

        if self.content:
            result["content"] = {
                media_type: content.to_dict()
                for media_type, content in self.content.items()
            }

        if self.links:
            result["links"] = {
                name: link.to_dict() for name, link in self.links.items()
            }

        return result

    def __repr__(self) -> str:
        return f"Response(description='{self.description}')"
