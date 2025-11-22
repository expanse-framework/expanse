from __future__ import annotations

from expanse.schematic.openapi.types.type import Type


class NullType(Type):
    def __init__(self):
        super().__init__("null")
