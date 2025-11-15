from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.schematic.openapi.path_item import PathItem
    from expanse.schematic.openapi.reference import Reference


class Callback:
    def __init__(self) -> None:
        self.expressions: dict[str, PathItem | Reference] = {}

    def add_expression(
        self, expression: str, path_item: PathItem | Reference
    ) -> Callback:
        self.expressions[expression] = path_item
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            expression: path_item.to_dict()
            for expression, path_item in self.expressions.items()
        }
