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
        self.description: str = description
        self.content: dict[str, MediaType] = {}
        self.required: bool = False

    def set_description(self, description: str) -> Self:
        self.description = description
        return self

    def set_content(self, content_type: str, media_type: MediaType) -> Self:
        self.content[content_type] = media_type
        return self

    def add_content(self, content_type: str, media_type: MediaType) -> Self:
        self.content[content_type] = media_type
        return self

    def set_required(self, required: bool) -> Self:
        self.required = required
        return self

    def to_dict(self) -> dict[str, Any]:
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
