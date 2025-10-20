from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.schematic.openapi.path_item import PathItem
    from expanse.schematic.openapi.reference import Reference


class Callback:
    """
    A map of possible out-of band callbacks related to the parent operation.
    Each value in the map is a Path Item Object that describes a set of requests
    that may be initiated by the API provider and the expected responses.
    The key value used to identify the path item object is an expression,
    evaluated at runtime, that identifies a URL to use for the callback operation.
    """

    def __init__(self) -> None:
        """Initialize a Callback object."""
        self.expressions: dict[str, PathItem | Reference] = {}

    def add_expression(
        self, expression: str, path_item: PathItem | Reference
    ) -> Callback:
        """
        Add a callback expression.

        Args:
            expression: A runtime expression that can be evaluated in the context
                       of a runtime HTTP request/response to identify the URL
                       to be used for the callback request.
            path_item: A Path Item Object, or a reference to one, used to define
                      a callback request and expected responses.

        Returns:
            Self for method chaining
        """
        self.expressions[expression] = path_item
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert the Callback object to a dictionary representation."""
        return {
            expression: path_item.to_dict()
            for expression, path_item in self.expressions.items()
        }

    def __repr__(self) -> str:
        return f"Callback({len(self.expressions)} expressions)"
