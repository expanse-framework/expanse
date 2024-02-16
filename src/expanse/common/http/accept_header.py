from __future__ import annotations

from typing import Self

from expanse.common.http.accept_header_item import AcceptHeaderItem


class AcceptHeader:
    def __init__(self, items: list[AcceptHeaderItem] | None) -> None:
        self._items: list[AcceptHeaderItem] = items or []
        self._sorted: bool = False

    @classmethod
    def from_string(cls, header: str) -> Self:
        values = [p.strip() for p in header.split(",")]

        return cls(
            [
                AcceptHeaderItem.from_string(value).set_index(i)
                for i, value in enumerate(values)
            ]
        )

    def all(self) -> list[AcceptHeaderItem]:
        self._sort()

        return self._items

    def __str__(self) -> str:
        return ", ".join(str(i) for i in self._items)

    def _sort(self) -> None:
        if self._sorted:
            return

        self._items.sort(key=lambda item: (-item.quality, item.index))
        self._sorted = True
