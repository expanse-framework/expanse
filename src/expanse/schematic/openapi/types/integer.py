from __future__ import annotations

from typing import Any

from expanse.schematic.openapi.types.type import Type


class IntegerType(Type):
    def __init__(self) -> None:
        super().__init__("integer")
        self.minimum: int | None = None
        self.maximum: int | None = None
        self.exclusive_minimum: int | None = None
        self.exclusive_maximum: int | None = None
        self.multiple_of: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()

        if self.minimum is not None:
            result["minimum"] = self.minimum
        if self.maximum is not None:
            result["maximum"] = self.maximum
        if self.exclusive_minimum is not None:
            result["exclusiveMinimum"] = self.exclusive_minimum
        if self.exclusive_maximum is not None:
            result["exclusiveMaximum"] = self.exclusive_maximum
        if self.multiple_of is not None:
            result["multipleOf"] = self.multiple_of

        return result
