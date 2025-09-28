from __future__ import annotations

from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from typing import Any
from typing import TypeVar
from typing import cast


T = TypeVar("T")  # Any type.


class MultiMapping[KT, VT](Mapping[KT, VT]):
    __slots__ = ("_dict", "_list")

    def __init__(
        self,
        raw: Mapping[KT, VT] | Iterable[tuple[KT, VT]] | None = None,
    ) -> None:
        _items: list[tuple[KT, VT]]
        if raw is None:
            _items = []
        elif isinstance(raw, MultiMapping):
            _items = cast("list[tuple[KT, VT]]", list(raw.multi_items()))
        elif isinstance(raw, Mapping):
            _items = cast("list[tuple[KT, VT]]", list(raw.items()))
        else:
            _items = list(raw)

        self._dict: dict[KT, VT] = dict(_items)
        self._list: list[tuple[KT, VT]] = _items

    def __getitem__(self, key: KT) -> VT:
        return self._dict[key]

    def __iter__(self) -> Iterator[KT]:
        return iter(self._dict)

    def __len__(self) -> int:
        return len(self._dict)

    def getlist(self, key: KT) -> list[VT]:
        return [item_value for item_key, item_value in self._list if item_key == key]

    def multi_items(self) -> list[tuple[KT, VT]]:
        return list(self._list)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return sorted(self._list) == sorted(other._list)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        items = self.multi_items()
        return f"{class_name}({items!r})"
