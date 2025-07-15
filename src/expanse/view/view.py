from collections.abc import Mapping
from typing import Any


class View:
    __slots__ = ("data", "identifier")

    def __init__(self, identifier: str, data: Mapping[str, Any] | None = None) -> None:
        self.identifier: str = identifier
        self.data: Mapping[str, Any] = data or {}
