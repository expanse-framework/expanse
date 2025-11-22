from __future__ import annotations

from typing import Any

from expanse.schematic.openapi.types.type import Type


class ArrayType(Type):
    def __init__(self) -> None:
        super().__init__("array")
        self.items: Any = None
        self.min_items: int | None = None
        self.max_items: int | None = None
        self.unique_items: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()

        if self.items is not None:
            if hasattr(self.items, "to_dict"):
                result["items"] = self.items.to_dict()
            else:
                result["items"] = self.items
        if self.min_items is not None:
            result["minItems"] = self.min_items
        if self.max_items is not None:
            result["maxItems"] = self.max_items
        if self.unique_items is not None:
            result["uniqueItems"] = self.unique_items

        return result
