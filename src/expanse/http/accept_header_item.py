from __future__ import annotations

import re

from typing import Self


class AcceptHeaderItem:
    def __init__(self, value: str, attributes: dict[str, str] | None = None) -> None:
        self._value: str = value
        self._attributes: dict[str, str] = {}
        self._quality: float = 1.0
        self._index: int = 0

        attributes = attributes or {}
        for name, value in attributes.items():
            self.set_attribute(name, value)

    @classmethod
    def from_string(cls, item: str) -> Self:
        parts = item.split(";", maxsplit=1)
        if len(parts) == 1:
            return cls(item)

        matches = re.findall(r"([^;=]+)=([^;=]+)", parts[1])
        attributes = {}

        for match in matches:
            attributes[match[0]] = match[1]

        return cls(parts[0], attributes)

    @property
    def value(self) -> str:
        return self._value

    @property
    def quality(self) -> float:
        return self._quality

    @property
    def index(self) -> int:
        return self._index

    def set_index(self, index: int) -> Self:
        self._index = index

        return self

    def set_attribute(self, name: str, value: str) -> Self:
        if name == "q":
            self._quality = float(value)
        else:
            self._attributes[name] = value

        return self

    def __str__(self) -> str:
        string = self._value

        if self._quality < 1.0:
            string += f";q={self._quality}"

        if self._attributes:
            string += f"; {';'.join(n + ' ' + v for n, v in self._attributes.items())}"

        return string
