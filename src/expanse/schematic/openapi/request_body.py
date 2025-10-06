from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Self


if TYPE_CHECKING:
    from expanse.schematic.openapi.media_type import MediaType


class RequestBody:
    """
    Describes a single request body.
    """

    def __init__(self, description: str = "") -> None:
        """
        Initialize a RequestBody object.

        Args:
            description: A brief description of the request body.
        """
        self.description: str = description
        self.content: dict[str, MediaType] = {}
        self.required: bool = False

    def set_description(self, description: str) -> Self:
        """
        Set a brief description of the request body.

        Args:
            description: A brief description of the request body. This could contain examples of use.
                        CommonMark syntax MAY be used for rich text representation.

        Returns:
            Self for method chaining
        """
        self.description = description
        return self

    def set_content(self, content_type: str, media_type: "MediaType") -> Self:
        """
        Set the content of the request body.

        Args:
            content_type: The media type (e.g., 'application/json')
            media_type: The media type object describing the content

        Returns:
            Self for method chaining
        """
        self.content[content_type] = media_type
        return self

    def add_content(self, content_type: str, media_type: "MediaType") -> Self:
        """
        Add content for a specific media type.

        Args:
            content_type: The media type (e.g., 'application/json')
            media_type: The media type object describing the content

        Returns:
            Self for method chaining
        """
        self.content[content_type] = media_type
        return self

    def set_required(self, required: bool) -> Self:
        """
        Set whether the request body is required in the request.

        Args:
            required: Determines if the request body is required in the request

        Returns:
            Self for method chaining
        """
        self.required = required
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the RequestBody object to a dictionary representation."""
        data: dict[str, Any] = {}

        if self.description:
            data["description"] = self.description

        if self.content:
            data["content"] = {
                content_type: media_type.to_dict()
                for content_type, media_type in self.content.items()
            }

        if self.required:
            data["required"] = self.required

        return data

    def __repr__(self) -> str:
        return (
            f"RequestBody(required={self.required}, content_types={len(self.content)})"
        )
