from __future__ import annotations

from expanse.schematic.openapi.types.type import Type


class BooleanType(Type):
    def __init__(self):
        super().__init__("boolean")
